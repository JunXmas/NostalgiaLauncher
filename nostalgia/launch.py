"""Dựng lệnh java và chạy game."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from .accounts import LaunchIdentity
from .install import Installer, rules_allow

CLASSPATH_SEP = ";" if os.name == "nt" else ":"
from .paths import APP_SLUG, APP_VERSION

LAUNCHER_NAME = APP_SLUG
LAUNCHER_VERSION = APP_VERSION


def find_java(major: int) -> str:
    """Tìm java phù hợp. MC 1.16- cần Java 8, 1.17-1.20.4 cần 17, 1.20.5+ cần 21."""
    candidates = []
    if java_home := os.environ.get("JAVA_HOME"):
        candidates.append(Path(java_home) / "bin" / "java")
    # Bố cục thư mục phổ biến trên Linux.
    for pattern in (f"/usr/lib/jvm/java-{major}-openjdk*", f"/usr/lib/jvm/*-{major}-*"):
        candidates.extend(p / "bin" / "java" for p in Path("/").glob(pattern.lstrip("/")))
    if system_java := shutil.which("java"):
        candidates.append(Path(system_java))

    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            out = subprocess.run(
                [str(candidate), "-version"], capture_output=True, text=True, timeout=10
            ).stderr
        except (OSError, subprocess.SubprocessError):
            continue
        if m := re.search(r'version "(\d+)(?:\.(\d+))?', out):
            first, second = int(m.group(1)), int(m.group(2) or 0)
            found = second if first == 1 else first  # "1.8.0_xxx" -> 8
            if found == major:
                return str(candidate)

    raise RuntimeError(
        f"Java {major} not found. Install it and set JAVA_HOME, "
        f"e.g. sudo apt install openjdk-{major}-jre"
    )


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

    cmd += [f"-Xmx{max_memory_mb}M", "-XX:+UseG1GC"]
    cmd.append(meta["mainClass"])

    if "arguments" in meta:
        cmd += _substitute(meta["arguments"]["game"], values, features)
    else:
        cmd += _substitute(meta["minecraftArguments"].split(), values, features)
        if identity.demo:
            cmd.append("--demo")  # bản cũ không có feature flag, phải tự thêm

    return cmd


def ensure_offline_libraries(meta: dict, installer: Installer) -> None:
    """Chạy offline thì không tải bù được, nên kiểm tra đủ file trước khi khởi động.

    Tương ứng bước EnsureOfflineLibraries của PrismLauncher.
    """
    version_id = meta["id"]
    needed = installer.library_paths(meta) + [installer.client_jar(meta)]
    missing = [p for p in needed if not p.exists()]
    if missing:
        listing = "\n".join(f"  {p}" for p in missing[:10])
        more = f"\n  ... and {len(missing) - 10} more" if len(missing) > 10 else ""
        raise RuntimeError(
            f"{len(missing)} file(s) missing, cannot run offline:\n{listing}{more}\n"
            "Run again online to finish downloading."
        )


def run(cmd: list[str], game_dir: Path) -> int:
    game_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        cmd, cwd=game_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in process.stdout:
        print(line, end="")
    return process.wait()
