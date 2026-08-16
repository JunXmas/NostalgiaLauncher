"""Kiểm tra bản phát hành mới trên GitHub và tải đúng installer cho hệ điều hành.

Không tự thay thế binary (bản cài chưa ký số, tự thay ngầm rất dễ hỏng và bị
Gatekeeper/SmartScreen chặn). Thay vào đó: báo có bản mới, rồi tải file cài phù
hợp về thư mục tải xuống và mở ra để người dùng bấm cài — an toàn, xuyên nền.
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
    """Chọn file cài đúng nền tảng: .exe cho Windows, .dmg (đúng kiến trúc) cho macOS."""
    system = platform.system()
    names = [(a.get("name", ""), a) for a in assets]
    if system == "Windows":
        return next((a for name, a in names if name.lower().endswith(".exe")), None)
    if system == "Darwin":
        arm = platform.machine().lower() in ("arm64", "aarch64")
        dmgs = [(name, a) for name, a in names if name.lower().endswith(".dmg")]
        if arm:
            hit = next((a for name, a in dmgs if "arm64" in name.lower()), None)
            if hit:
                return hit
        # Intel hoặc không rõ: ưu tiên file không phải arm64, rồi tới bất kỳ .dmg nào.
        return next((a for name, a in dmgs if "arm64" not in name.lower()),
                    dmgs[0][1] if dmgs else None)
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
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def install(path: Path) -> str:
    """Cài đặt bản đã tải thẳng vào máy. Trả về mode cho phía gọi xử lý tiếp:

    - 'quit'      (Windows): đã chạy installer im lặng ở nền; app PHẢI thoát ngay
                  để installer thay được file .exe đang bị khoá — Inno tự đóng &
                  mở lại app. Bản cài per-user nên không cần quyền admin.
    - 'installed' (Linux .deb qua pkexec): đã cài xong (một hộp thoại xin mật
                  khẩu); phía gọi mời khởi động lại. Tự kéo cả thư viện phụ thuộc.
    - 'opened'    (macOS .dmg hoặc thiếu công cụ): mở file cho người dùng tự cài.

    Ném lỗi nếu lệnh cài thất bại — phía gọi bắt để lùi về mở file thủ công.
    """
    system = platform.system()
    suffix = path.suffix.lower()
    if system == "Windows" and suffix == ".exe":
        subprocess.Popen([str(path), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                          "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"])
        return "quit"
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
