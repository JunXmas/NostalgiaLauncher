"""Dựng lệnh java và chạy game."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .accounts import LaunchIdentity
from .install import CURRENT_OS, Installer, rules_allow

CLASSPATH_SEP = ";" if os.name == "nt" else ":"

# Trên Windows, một tiến trình con luôn kèm cửa sổ console đen. Với bản GUI đã
# đóng gói thì cửa sổ đó vừa xấu vừa vô dụng — và người dùng đóng nhầm nó là
# game tắt theo. CREATE_NO_WINDOW dẹp nó mà vẫn giữ nguyên đường ống stdout, nên
# log game vẫn chảy về launcher như thường.
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
from .paths import APP_SLUG, APP_VERSION

LAUNCHER_NAME = APP_SLUG
LAUNCHER_VERSION = APP_VERSION


JAVA_EXE = "java.exe" if os.name == "nt" else "java"


def _system_java_candidates(major: int) -> list[Path]:
    """Những chỗ Java hay được cài, theo quy ước từng hệ điều hành."""
    found: list[Path] = []
    if os.name == "nt":
        # Bản cài Windows luôn đặt dưới Program Files, mỗi nhà phát hành một thư mục.
        roots = [
            Path(p)
            for p in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"))
            if p
        ]
        vendors = ("Java", "Eclipse Adoptium", "Microsoft", "Zulu", "Amazon Corretto", "BellSoft")
        for root in roots:
            for vendor in vendors:
                if not (root / vendor).is_dir():
                    continue
                found.extend((root / vendor).glob(f"*{major}*/bin/{JAVA_EXE}"))
        return found

    if sys.platform == "darwin":
        # java_home là cách chính chủ của macOS để hỏi "JDK bản X nằm đâu"; nó biết
        # cả những bộ cài mà việc quét thư mục thuần tuý bỏ sót.
        try:
            out = subprocess.run(
                ["/usr/libexec/java_home", "-v", str(major)],
                capture_output=True, text=True, timeout=10,
            )
            if out.returncode == 0 and out.stdout.strip():
                found.append(Path(out.stdout.strip()) / "bin" / "java")
        except (OSError, subprocess.SubprocessError):
            pass
        found.extend(
            Path("/Library/Java/JavaVirtualMachines").glob(f"*{major}*/Contents/Home/bin/java")
        )
        return found

    # Linux và Unix khác.
    for pattern in (f"java-{major}-openjdk*", f"*-{major}-*"):
        found.extend(p / "bin" / "java" for p in Path("/usr/lib/jvm").glob(pattern))
    return found


def _install_hint(major: int) -> str:
    if os.name == "nt":
        return f"Download Java {major} from adoptium.net, then restart the launcher."
    if sys.platform == "darwin":
        return f"Install it with `brew install openjdk@{major}`, or from adoptium.net."
    return f"Install it, e.g. `sudo apt install openjdk-{major}-jre`."


def find_java(major: int) -> str:
    """Tìm java phù hợp. MC 1.16- cần Java 8, 1.17-1.20.4 cần 17, 1.20.5+ cần 21."""
    candidates = []
    if java_home := os.environ.get("JAVA_HOME"):
        candidates.append(Path(java_home) / "bin" / JAVA_EXE)
    candidates.extend(_system_java_candidates(major))
    if system_java := shutil.which("java"):
        candidates.append(Path(system_java))

    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            out = subprocess.run(
                [str(candidate), "-version"],
                capture_output=True, text=True, timeout=10, **NO_WINDOW,
            ).stderr
        except (OSError, subprocess.SubprocessError):
            continue
        if m := re.search(r'version "(\d+)(?:\.(\d+))?', out):
            first, second = int(m.group(1)), int(m.group(2) or 0)
            found = second if first == 1 else first  # "1.8.0_xxx" -> 8
            if found == major:
                return str(candidate)

    raise RuntimeError(f"Java {major} not found. {_install_hint(major)}")


def resolve_java(meta: dict, game_dir: Path) -> str:
    """Chọn java: ưu tiên JRE do launcher tải sẵn, rồi mới tới Java hệ thống.

    JRE tải sẵn (Mojang cấp) khớp chính xác phiên bản game cần, nên đáng tin hơn
    Java lung tung trên máy. Không có JRE tải sẵn thì mới dò hệ thống.
    """
    from . import jre  # tránh vòng import lúc nạp module

    component = jre.component_of(meta)
    if jre.is_installed(game_dir, component):
        return str(jre.java_binary(game_dir, component))
    return find_java(meta.get("javaVersion", {}).get("majorVersion", 8))


def _substitute(args: list, values: dict[str, str], features: dict[str, bool]) -> list[str]:
    """Trải phần `arguments` của version JSON, áp rule và thay biến ${...}."""
    out: list[str] = []
    for arg in args:
        if isinstance(arg, dict):
            if not rules_allow(arg.get("rules"), features):
                continue
            value = arg["value"]
            out.extend([value] if isinstance(value, str) else value)
        else:
            out.append(arg)
    return [re.sub(r"\$\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), a) for a in out]


def build_command(
    meta: dict,
    installer: Installer,
    identity: LaunchIdentity,
    *,
    java: str | None = None,
    max_memory_mb: int = 2048,
) -> list[str]:
    version_id = meta["id"]
    classpath = installer.library_paths(meta) + [installer.client_jar(meta)]
    asset_index = meta["assetIndex"]["id"]

    values = {
        "auth_player_name": identity.username,
        "auth_uuid": identity.uuid.replace("-", ""),
        "auth_access_token": identity.access_token,
        "auth_session": f"token:{identity.access_token}",
        "user_type": identity.user_type,
        "user_properties": "{}",  # placeholder của bản 1.7-1.8, nay luôn rỗng
        "clientid": "",
        "auth_xuid": "",
        "version_name": version_id,
        "version_type": meta.get("type", "release"),
        "game_directory": str(installer.game_dir),
        "assets_root": str(installer.assets_dir),
        "game_assets": str(installer.assets_dir / "virtual" / asset_index),
        "assets_index_name": asset_index,
        "natives_directory": str(installer.natives_dir(meta)),
        "launcher_name": LAUNCHER_NAME,
        "launcher_version": LAUNCHER_VERSION,
        "classpath": CLASSPATH_SEP.join(str(p) for p in classpath),
        "classpath_separator": CLASSPATH_SEP,
        "library_directory": str(installer.libraries_dir),
    }
    # Rule `is_demo_user` trong version JSON tự sinh ra cờ --demo cho ta.
    features = {"is_demo_user": identity.demo, "has_custom_resolution": False}

    cmd = [java or resolve_java(meta, installer.game_dir)]

    if "arguments" in meta:  # 1.13 trở lên
        cmd += _substitute(meta["arguments"]["jvm"], values, features)
    else:  # bản cũ không khai báo JVM args
        cmd += [f"-Djava.library.path={values['natives_directory']}", "-cp", values["classpath"]]
        # Bản ≤1.12 (LWJGL2) không tự thêm cờ này. Trên macOS, LWJGL/GLFW bắt buộc
        # tạo cửa sổ trên luồng đầu tiên; thiếu -XstartOnFirstThread là crash ngay.
        if CURRENT_OS == "osx":
            cmd.append("-XstartOnFirstThread")

    cmd += [f"-Xmx{max_memory_mb}M", "-XX:+UseG1GC"]
    cmd.append(meta["mainClass"])

    if "arguments" in meta:
        cmd += _substitute(meta["arguments"]["game"], values, features)
    else:
        cmd += _substitute(meta["minecraftArguments"].split(), values, features)
        if identity.demo:
            cmd.append("--demo")  # bản cũ không có feature flag, phải tự thêm

    return cmd


class OfflineLaunchError(RuntimeError):
    """Không đủ dữ liệu dưới đĩa để chạy khi mất mạng.

    Kế thừa RuntimeError để chỗ nào đang bắt RuntimeError vẫn bắt được như cũ.
    """


def ensure_offline_libraries(meta: dict, installer: Installer) -> list[str]:
    """Chạy offline thì không tải bù được, nên kiểm tra đủ file trước khi khởi động.

    Tương ứng bước EnsureOfflineLibraries của PrismLauncher.

    Phân biệt hai mức: thiếu jar hay natives thì JVM chết ngay -> ném lỗi; thiếu
    assets thì game vẫn chạy, chỉ mất âm thanh và bản dịch -> trả về cảnh báo để
    bên gọi hiển thị. Chỉ kiểm tra sự tồn tại, không băm SHA1: băm vài nghìn file
    mất hàng chục giây, mà thứ ta cần biết ở đây chỉ là "có hay không".
    """
    needed = installer.library_paths(meta) + [installer.client_jar(meta)]
    missing = [p for p in needed if not p.exists()]
    if missing:
        listing = "\n".join(f"  {p}" for p in missing[:10])
        more = f"\n  ... and {len(missing) - 10} more" if len(missing) > 10 else ""
        raise OfflineLaunchError(
            f"{len(missing)} file(s) missing, cannot run offline:\n{listing}{more}\n"
            "Run again online to finish downloading."
        )

    # Natives được giải nén ra thư mục riêng; xoá nhầm thư mục đó thì lỗi hiện ra
    # dưới dạng UnsatisfiedLinkError giữa lúc game đang mở, rất khó đoán.
    wants_natives = any("natives" in lib for lib in meta.get("libraries", []))
    natives = installer.natives_dir(meta)
    if wants_natives and not (natives.is_dir() and any(natives.iterdir())):
        raise OfflineLaunchError(
            f"Native libraries have not been extracted: {natives}\n"
            "Run again online to finish installing."
        )

    warnings: list[str] = []
    index_id = meta.get("assetIndex", {}).get("id")
    if index_id:
        index_path = installer.assets_dir / "indexes" / f"{index_id}.json"
        if not index_path.exists():
            warnings.append(
                f"Asset index {index_id} is missing — the game will start without "
                "sounds or translations."
            )
        else:
            try:
                objects = json.loads(index_path.read_text())["objects"]
            except (OSError, ValueError, KeyError):
                warnings.append(f"Asset index {index_id} is unreadable.")
            else:
                absent = sum(
                    1
                    for obj in objects.values()
                    if not (installer.assets_dir / "objects"
                            / obj["hash"][:2] / obj["hash"]).exists()
                )
                if absent:
                    warnings.append(
                        f"{absent}/{len(objects)} asset files are missing — expect "
                        "silent audio or missing translations."
                    )
    return warnings


def launch_game_offline(
    version_id: str,
    installer: Installer,
    identity: LaunchIdentity,
    *,
    java: str | None = None,
    max_memory_mb: int = 2048,
    on_status=None,
) -> int:
    """Khởi chạy game mà không phát một request mạng nào.

    Khác với đường chạy thường ở đúng ba chỗ, và cả ba đều cần thiết:

    1. Đọc version JSON bằng offline_version_json() — bản thường sẽ gọi manifest
       của Mojang khi thiếu file.
    2. Kiểm tra đủ dữ liệu TRƯỚC, thay vì gọi installer.install(). install() coi
       "file đã có và đúng hash" là không cần tải, nên phần lớn trường hợp nó chạy
       lọt khi offline — nhưng chỉ cần một file lẻ bị thiếu là nó ném
       ConnectionError sau khi đã băm hết vài trăm MB. Kiểm tra trước thì hỏng
       trong một phần giây và nói rõ thiếu gì.
    3. Chọn Java chỉ từ những gì đã có trên máy: resolve_java() không tải JRE,
       nhưng thông báo lỗi mặc định của nó không nhắc rằng ta đang offline.

    Trả về mã thoát của tiến trình game.
    """
    def say(message: str) -> None:
        if on_status:
            on_status(message)

    meta = installer.offline_version_json(version_id)
    for warning in ensure_offline_libraries(meta, installer):
        say(f"[warning] {warning}")

    try:
        java_bin = java or resolve_java(meta, installer.game_dir)
    except RuntimeError as e:
        raise OfflineLaunchError(
            f"{e}\n(Offline mode cannot download the Java runtime for you.)"
        ) from e

    cmd = build_command(meta, installer, identity, java=java_bin,
                        max_memory_mb=max_memory_mb)
    say(f"Launching {version_id} offline as '{identity.username}'"
        + (" (demo)" if identity.demo else ""))
    return run(cmd, installer.game_dir)


def run(cmd: list[str], game_dir: Path) -> int:
    game_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        cmd, cwd=game_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", **NO_WINDOW,
    )
    for line in process.stdout:
        print(line, end="")
    return process.wait()
