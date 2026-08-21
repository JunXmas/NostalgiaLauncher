"""Kiểm tra bản phát hành mới trên GitHub và TỰ tải + cài trên cả ba nền tảng.

Báo có bản mới, rồi tải đúng file cài cho hệ điều hành và cài thẳng — không bắt
người dùng lên GitHub tải tay nữa:
  • Windows: chạy installer Inno im lặng, tự đóng & mở lại app.
  • macOS:   mount .dmg, thay .app đang chạy bằng bản mới, tự mở lại.
  • Linux:   cài .deb qua pkexec (một lần nhập mật khẩu), tự mở lại.
Nếu thiếu công cụ hoặc lỗi, lùi an toàn về mở file / trang release cho người dùng.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import requests

from . import __version__


def clean_child_env() -> dict:
    """Env để spawn chương trình NGOÀI bundle (trình duyệt, file manager, installer).

    Bản đóng gói PyInstaller đặt LD_LIBRARY_PATH (macOS: DYLD_LIBRARY_PATH) tới thư
    mục lib bundle. Tiến trình con thừa hưởng biến đó sẽ nạp nhầm lib bundle rồi
    chết lặng — 'Open folder', các link, và cả việc mở installer đều im ru. Trả
    biến về giá trị gốc PyInstaller lưu ở *_ORIG (hoặc bỏ hẳn nếu vốn không có).
    Chạy từ mã nguồn thì các biến này không tồn tại nên đây là no-op.
    """
    env = os.environ.copy()
    for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        original = env.pop(var + "_ORIG", None)
        if original is not None:
            env[var] = original
        else:
            env.pop(var, None)
    return env

REPO = "JunXmas/NostalgiaLauncher"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
TIMEOUT = 15


def _parse(tag: str) -> tuple:
    """'v0.2.1' -> (0, 2, 1). Phần không phải số coi như 0 để so sánh an toàn."""
    nums = tag.lstrip("vV").split("-")[0].split(".")
    out = []
    for n in nums:
        try:
            out.append(int(n))
        except ValueError:
            out.append(0)
    return tuple(out)


def _os_asset(assets: list[dict]) -> dict | None:
    """Chọn file cài đúng nền tảng: .exe (Windows), .dmg (macOS), .deb (Linux)."""
    system = platform.system()
    machine = platform.machine().lower()
    names = [(a.get("name", ""), a) for a in assets]
    if system == "Windows":
        return next((a for name, a in names if name.lower().endswith(".exe")), None)
    if system == "Darwin":
        arm = machine in ("arm64", "aarch64")
        dmgs = [(name, a) for name, a in names if name.lower().endswith(".dmg")]
        if arm:
            hit = next((a for name, a in dmgs if "arm64" in name.lower()), None)
            if hit:
                return hit
        # Intel hoặc không rõ: ưu tiên file không phải arm64, rồi tới bất kỳ .dmg nào.
        return next((a for name, a in dmgs if "arm64" not in name.lower()),
                    dmgs[0][1] if dmgs else None)
    if system == "Linux":
        want = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        debs = [(name, a) for name, a in names if name.lower().endswith(".deb")]
        hit = next((a for name, a in debs if want in name.lower()), None)
        return hit or (debs[0][1] if debs else None)
    return None


def check() -> dict | None:
    """Trả về thông tin bản mới nếu có (newer than __version__), ngược lại None.

    /releases/latest chỉ tính bản đã publish (bỏ qua draft & prerelease), nên
    bản nháp đang chờ duyệt sẽ không làm phiền người dùng.
    """
    r = requests.get(LATEST_URL, timeout=TIMEOUT,
                     headers={"Accept": "application/vnd.github+json"})
    r.raise_for_status()
    data = r.json()
    tag = data.get("tag_name", "")
    if not tag or _parse(tag) <= _parse(__version__):
        return None
    return {
        "version": tag.lstrip("vV"),
        "tag": tag,
        "page_url": data.get("html_url", f"https://github.com/{REPO}/releases"),
        "notes": (data.get("body") or "").strip(),
        "asset": _os_asset(data.get("assets", [])),
    }


def download_asset(asset: dict) -> Path:
    """Tải file cài về thư mục Downloads (hoặc home) và trả về đường dẫn."""
    dest_dir = Path.home() / "Downloads"
    if not dest_dir.is_dir():
        dest_dir = Path.home()
    dest = dest_dir / asset["name"]
    with requests.get(asset["browser_download_url"], stream=True, timeout=120) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in resp.iter_content(1 << 16):
                f.write(chunk)
        tmp.replace(dest)
    return dest


def _open(path: Path) -> None:
    """Mở file bằng trình xử lý mặc định (để người dùng tự cài)."""
    if platform.system() == "Windows":
        os.startfile(str(path))          # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)], env=clean_child_env())
    else:
        subprocess.Popen(["xdg-open", str(path)], env=clean_child_env())


def _current_app_bundle() -> Path | None:
    """Đường dẫn .app đang chạy trên macOS (…/Nostalgia Launcher.app)."""
    if not getattr(sys, "frozen", False):
        return None
    for parent in Path(sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return parent
    return None


def _install_dmg_macos(dmg: Path) -> str:
    """Tự cập nhật trên macOS: mount .dmg, thay .app đang chạy bằng bản mới, mở lại.

    App đang chạy không tự ghi đè chính nó được, nên ghi một script chờ app thoát
    rồi mới copy đè + mở lại; app trả 'quit' để thoát ngay cho script làm việc.
    """
    import tempfile
    dest = _current_app_bundle()
    if dest is None:
        _open(dmg)                       # chạy từ nguồn / không rõ vị trí -> mở tay
        return "opened"
    mount = tempfile.mkdtemp(prefix="nl-dmg-")
    subprocess.run(["hdiutil", "attach", str(dmg), "-nobrowse", "-noverify",
                    "-noautoopen", "-mountpoint", mount], check=True, env=clean_child_env())
    apps = list(Path(mount).glob("*.app"))
    if not apps:
        subprocess.run(["hdiutil", "detach", mount, "-quiet"], env=clean_child_env())
        raise RuntimeError("The disk image has no app to install.")
    new_app, script = apps[0], Path(tempfile.mkstemp(prefix="nl-upd-", suffix=".sh")[1])
    script.write_text(
        "#!/bin/bash\n"
        "sleep 1\n"
        f'app="{dest}"\n'
        'for i in $(seq 1 120); do pgrep -f "$app/Contents/MacOS/" >/dev/null || break; sleep 0.5; done\n'
        f'/usr/bin/ditto "{new_app}" "$app.new" && /bin/rm -rf "$app" && /bin/mv "$app.new" "$app"\n'
        f'/usr/bin/hdiutil detach "{mount}" -quiet || true\n'
        '/usr/bin/open "$app"\n'
        f'/bin/rm -f "{script}"\n'
    )
    script.chmod(0o755)
    subprocess.Popen(["/bin/bash", str(script)], env=clean_child_env(),
                     start_new_session=True)
    return "quit"                        # thoát ngay để script thay .app rồi mở lại


def install(path: Path) -> str:
    """Cài đặt bản đã tải thẳng vào máy. Trả về mode cho phía gọi xử lý tiếp:

    - 'quit'      (Windows / macOS): tiến trình cài đang chạy nền chờ app thoát để
                  thay file rồi tự mở lại; app PHẢI thoát ngay.
    - 'installed' (Linux .deb qua pkexec): đã cài xong; phía gọi tự mở lại.
    - 'opened'    (thiếu công cụ): đã mở file cho người dùng tự cài.

    Ném lỗi nếu lệnh cài thất bại — phía gọi bắt để lùi về mở trang release.
    """
    system = platform.system()
    suffix = path.suffix.lower()
    if system == "Windows" and suffix == ".exe":
        subprocess.Popen([str(path), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                          "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"])
        return "quit"
    if system == "Darwin" and suffix == ".dmg":
        return _install_dmg_macos(path)
    if system == "Linux" and suffix == ".deb" and shutil.which("pkexec"):
        subprocess.run(["pkexec", "apt-get", "install", "-y", str(path)], check=True)
        return "installed"
    _open(path)
    return "opened"


def relaunch() -> None:
    """Mở lại launcher bằng bản vừa cài rồi để tiến trình cũ tự thoát."""
    if getattr(sys, "frozen", False):
        # Bản đóng gói: chạy lại chính file thực thi (đã được thay bằng bản mới).
        subprocess.Popen([sys.executable])
    else:
        # Chạy từ mã nguồn: khởi động lại module.
        subprocess.Popen([sys.executable, "-m", "nostalgia", "gui"])
