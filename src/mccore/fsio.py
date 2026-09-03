"""Thao tác file dùng chung: ghi nguyên tử, băm, và ghép đường dẫn an toàn.

Ba việc ở đây đều nhỏ nhưng làm sai thì hỏng theo kiểu khó thấy: ghi không nguyên tử để lại
file cụt sau một lần Ctrl-C, ghép đường dẫn không kiểm để archive tải từ mạng ghi đè ra
ngoài thư mục đích, và băm sai thuật toán thì không đối chiếu được với gì cả.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from mccore.errors import DataFileError, UnsafePathError

# JSON đọc từ đĩa hay từ mạng là dữ liệu KHÔNG tin được, nên kiểu của nó phải nói đúng điều
# đó. Dùng `Any` sẽ khiến bộ kiểm kiểu im lặng ở mọi chỗ dùng sau này; kiểu đệ quy này buộc
# người gọi phải thu hẹp kiểu trước khi dùng.
type JsonValue = bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"] | None

READ_CHUNK = 1 << 20

# Chỉ chủ sở hữu đọc/ghi. Dùng cho file có thể chứa vé đăng nhập.
PRIVATE_FILE_MODE = 0o600
# `mkstemp` tạo file với quyền 0600; file thường cần quyền đọc như mọi file khác.
DEFAULT_FILE_MODE = 0o644


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_join(base: Path, relative: str) -> Path:
    """Ghép `relative` vào trong `base`, từ chối mọi đường thoát ra ngoài.

    Dùng cho mọi đường dẫn đến từ bên ngoài: tên entry trong zip natives, tên file trong
    modpack, đường dẫn trong manifest JRE. Kiểu tấn công kinh điển là một entry tên
    `../../.bashrc`; ở đây nó thành `UnsafePathError` chứ không thành file bị ghi đè.

    Chặn cả đường dẫn tuyệt đối và symlink trỏ ra ngoài.
    """
    # Kiểm theo cả hai quy ước: archive có thể do máy Windows tạo ra, nên `C:\x`, `\\máy\ổ`
    # và `\x` đều phải bị chặn kể cả khi đang chạy trên Linux.
    #
    # Không dùng riêng `is_absolute()`: với Windows, `\x` KHÔNG được coi là tuyệt đối (thiếu
    # tên ổ) nhưng vẫn trỏ về gốc ổ hiện tại, tức vẫn thoát ra ngoài. Phải xét cả `root`.
    windows_path = PureWindowsPath(relative)
    if PurePosixPath(relative).is_absolute() or windows_path.root or windows_path.drive:
        message = f"đường dẫn tuyệt đối không được chấp nhận: {relative!r}"
        raise UnsafePathError(message)

    base_resolved = base.resolve()
    target = (base_resolved / relative).resolve()
    if target != base_resolved and base_resolved not in target.parents:
        message = f"đường dẫn thoát ra ngoài {base_resolved}: {relative!r}"
        raise UnsafePathError(message)
    return target


def sha1_of_file(path: Path) -> str:
    """Băm sha1 của một file, đọc theo khối để không nạp cả file vào bộ nhớ.

    sha1 là ràng buộc giao thức chứ không phải lựa chọn bảo mật: manifest của Mojang công bố
    sha1, nên muốn đối chiếu thì phải dùng đúng sha1. Bộ soi mã sẽ gắn cờ "hàm băm không an
    toàn" — đổi sang sha256 thì không còn gì để đối chiếu.
    """
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while chunk := handle.read(READ_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> JsonValue:
    """Đọc JSON, biến mọi kiểu hỏng thành một lỗi duy nhất kèm đường dẫn.

    Người gọi cần biết *file nào* hỏng; `JSONDecodeError` trần không nói điều đó, và
    `FileNotFoundError` lẫn với lỗi mạng khi đọc log.
    """
    try:
        # json.loads khai trả `Any`; ép về JsonValue ngay tại biên để cái `Any` đó không
        # lan ra khắp nơi và làm bộ kiểm kiểu mất tác dụng ở mọi chỗ dùng sau.
        parsed: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        message = f"không tìm thấy file: {path}"
        raise DataFileError(message) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        message = f"file JSON hỏng: {path}"
        raise DataFileError(message) from exc
    return parsed


def atomic_write_json(path: Path, data: JsonValue, *, private: bool = False) -> None:
    """Ghi JSON theo kiểu hoặc-được-hoặc-không: file cũ chỉ biến mất khi file mới đã xong.

    Ghi ra file tạm cùng thư mục, `fsync`, rồi `os.replace` — `replace` là nguyên tử trên
    cùng một hệ thống file. Nếu ghi thẳng vào đích, một lần mất điện giữa chừng sẽ để lại
    file cụt mà lần chạy sau đọc vào là hỏng.

    `private=True` đặt quyền 0600, dùng cho file có thể chứa vé đăng nhập.
    """
    ensure_dir(path.parent)
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(PRIVATE_FILE_MODE if private else DEFAULT_FILE_MODE)
        temp_path.replace(path)
    except BaseException:
        # Kể cả khi bị Ctrl-C: không để lại file tạm nằm rác cạnh file thật.
        temp_path.unlink(missing_ok=True)
        raise


def set_executable(path: Path) -> None:
    """Bật cờ thực thi, giữ nguyên các quyền sẵn có.

    Cần cho `bin/java` sau khi bung JRE của Mojang: manifest có khai cờ thực thi nhưng
    `zipfile` không khôi phục nó, và một JRE không có cờ này thì không chạy được.
    """
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
