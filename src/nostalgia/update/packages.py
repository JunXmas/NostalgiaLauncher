"""Cài bản mới bằng CHÍNH gói của hệ thống, cho những kiểu cài không tráo thư mục được.

`apply.py` tráo thư mục onedir tại chỗ — chỉ chạy được khi launcher nằm trong thư mục ghi
được. Ba kiểu cài phổ biến thì không:

  • AppImage — chạy từ squashfs gắn chỉ-đọc, nhưng CHÍNH file `.AppImage` trên đĩa thì ghi
    đè được. Thay file rồi mở lại là xong, không cần quyền quản trị.
  • `.deb` / `.rpm` — cài ở `/opt`, chủ là root. Trình quản lý gói của hệ mới có quyền;
    gọi qua `pkexec` để người dùng nhập mật khẩu một lần trong hộp thoại của hệ điều hành.

Không có `pkexec` (hoặc người dùng bấm Huỷ) thì KHÔNG cố vòng khác — không bao giờ tự nâng
quyền bằng đường lén. Người gọi lùi về mở trang tải.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from nostalgia.errors import UpdateError
from nostalgia.storage.files import set_executable
from nostalgia.update.apply import clean_child_env

# Lệnh cài cho từng đuôi gói. `-y` vì hộp thoại pkexec đã là lần hỏi của người dùng rồi;
# hỏi thêm ở stdin thì không ai thấy để trả lời, tiến trình treo mãi.
_INSTALL_COMMANDS: dict[str, tuple[str, ...]] = {
    ".deb": ("apt-get", "install", "-y"),
    ".rpm": ("dnf", "install", "-y"),
}


def appimage_path() -> Path | None:
    """File `.AppImage` đang chạy, theo biến `APPIMAGE` do runtime AppImage đặt."""
    value = os.environ.get("APPIMAGE")
    return Path(value) if value else None


def replace_appimage(downloaded: Path, target: Path) -> None:
    """Ghi đè file AppImage đang chạy bằng bản vừa tải, giữ quyền chạy.

    Ghi qua file tạm cùng thư mục rồi `replace` (nguyên tử trên cùng filesystem): mất điện
    giữa chừng thì còn file cũ nguyên vẹn, chứ không để lại một file cụt không chạy được.

    Ghi đè file của MỘT tiến trình đang chạy là an toàn trên Linux: `replace` thay tên trong
    thư mục, inode cũ sống tới khi tiến trình thoát.
    """
    if not os.access(target.parent, os.W_OK):
        raise UpdateError(
            f"không ghi được vào {target.parent} — chép file .AppImage mới vào đó bằng tay"
        )
    staging = target.with_name(target.name + ".new")
    shutil.copyfile(downloaded, staging)
    set_executable(staging)
    staging.replace(target)


def install_system_package(package_path: Path) -> None:
    """Cài `.deb`/`.rpm` qua `pkexec` (hộp thoại xin mật khẩu của hệ điều hành).

    Ném `UpdateError` khi thiếu `pkexec`, khi đuôi gói lạ, hoặc khi người dùng bấm Huỷ —
    người gọi lùi về mở trang tải. Không nuốt lỗi: cài hỏng mà im lặng thì người dùng tưởng
    đã lên bản mới trong khi vẫn đang chạy bản cũ.
    """
    command = _INSTALL_COMMANDS.get(package_path.suffix.lower())
    if command is None:
        raise UpdateError(f"không biết cách cài {package_path.name}")
    if not shutil.which("pkexec"):
        raise UpdateError("máy không có pkexec để xin quyền cài đặt — cài gói bằng tay")
    if not shutil.which(command[0]):
        raise UpdateError(f"máy không có {command[0]} để cài {package_path.suffix}")
    completed = subprocess.run(
        ["pkexec", *command, str(package_path)],
        env=clean_child_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        # 126 = người dùng bấm Huỷ hoặc không được phép; nói đúng chuyện đó thay vì dội
        # nguyên stderr của apt vào mặt người dùng.
        if completed.returncode == 126:
            raise UpdateError("bạn đã huỷ hộp thoại xin quyền — chưa cài gì cả")
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        raise UpdateError(f"cài {package_path.name} thất bại: {detail[-1] if detail else 'lỗi lạ'}")


def relaunch(executable: Path) -> None:
    """Mở lại launcher rồi để tiến trình hiện tại tự thoát (người gọi lo việc thoát)."""
    subprocess.Popen(
        [str(executable)],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        env=clean_child_env(),
    )
