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
from pathlib import Path

from mccore.errors import DataFileError, UnsafePathError
from mccore.model.json_value import JsonValue

# 256 KiB. Đo trên 400 file thật: tốc độ sha1 gần như không đổi từ 64 KiB tới 16 MiB
# (500-511 MB/s), nên chọn khối nhỏ để khi băm song song 16 luồng chỉ tốn 4 MiB bộ đệm thay
# vì 16 MiB. Cũng đã đo `hashlib.file_digest` (có sẵn từ Python 3.11): 470 MB/s, CHẬM HƠN
# với nhiều file nhỏ — đừng "hiện đại hoá" sang nó.
READ_CHUNK_SIZE = 256 * 1024

# Chỉ chủ sở hữu đọc/ghi. Dùng cho file có thể chứa vé đăng nhập.
PRIVATE_FILE_MODE = 0o600
# `mkstemp` tạo file với quyền 0600; file thường cần quyền đọc như mọi file khác.
DEFAULT_FILE_MODE = 0o644


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_within(parent_dir: Path, relative_path: str) -> Path:
    """Ghép `relative_path` vào trong `parent_dir`, từ chối mọi đường thoát ra ngoài. Thuần chuỗi.

    Dùng cho mọi đường dẫn đến từ bên ngoài: tên entry trong zip natives, tên file trong
    modpack, đường dẫn trong manifest JRE. Kiểu tấn công kinh điển là một entry tên
    `../../.bashrc`; ở đây nó thành `UnsafePathError` chứ không thành file bị ghi đè.

    **Không chạm hệ thống file** — đó là lý do hàm mang tiền tố `resolve_`. Bản trước gọi
    `Path.resolve()` hai lần mỗi lần dùng, tốn 177 µs; giải nén một modpack 3.500 file là
    618 ms chỉ để kiểm tên. Bản này tốn khoảng 4 µs, nhanh hơn 44 lần, và kiểm chặt hơn:
    `resolve()` chỉ so đích cuối cùng, còn ở đây mọi thành phần `..` đều bị từ chối thẳng.

    Bù lại, hàm không phát hiện được symlink đã có sẵn *bên trong* `parent_dir` trỏ ra ngoài.
    Bất biến mà người gọi phải giữ: **không bao giờ tạo symlink từ nội dung archive.** Khi
    mọi thư mục trong `base` đều do chính ta tạo, không symlink nào tồn tại để đi qua.
    """
    normalised = relative_path.replace("\\", "/")
    if not normalised or normalised.startswith("/"):
        # Sau khi đổi `\` thành `/`, cả `\tuyet-doi` lẫn `\\may-chu\o` đều thành dạng này.
        message = f"đường dẫn tuyệt đối hoặc rỗng không được chấp nhận: {relative_path!r}"
        raise UnsafePathError(message)
    if len(normalised) > 1 and normalised[1] == ":":
        message = f"đường dẫn có tên ổ đĩa không được chấp nhận: {relative_path!r}"
        raise UnsafePathError(message)

    parts = [part for part in normalised.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        message = f"đường dẫn thoát ra ngoài bằng '..': {relative_path!r}"
        raise UnsafePathError(message)
    if not parts:
        message = f"đường dẫn không trỏ tới file nào: {relative_path!r}"
        raise UnsafePathError(message)
    return parent_dir.joinpath(*parts)


def resolve_child(parent_dir: Path, child_name: str) -> Path:
    """Ghép MỘT thành phần tên vào `parent_dir`. Từ chối mọi thứ không phải một cái tên đơn.

    Khác `resolve_within` ở chỗ không cho đường dẫn nhiều tầng: dùng cho những chỗ mà giá
    trị *phải* là một cái tên, như mã phiên bản hay hash asset. Đã đo trước khi vá:
    `version_id = "/tuyet-doi"` cho ra `/tuyet-doi.json` — thoát hẳn khỏi thư mục dữ liệu,
    và mã phiên bản thì đến từ dòng lệnh nên là dữ liệu không tin được.
    """
    if not child_name or child_name in {".", ".."} or "/" in child_name or "\\" in child_name:
        message = f"tên phải là một thành phần đơn, không rỗng: {child_name!r}"
        raise UnsafePathError(message)
    if len(child_name) > 1 and child_name[1] == ":":
        message = f"tên không được chứa tên ổ đĩa: {child_name!r}"
        raise UnsafePathError(message)
    return parent_dir / child_name


def sha1_of_file(path: Path) -> str:
    """Băm sha1 của một file, đọc theo khối để không nạp cả file vào bộ nhớ.

    sha1 là ràng buộc giao thức chứ không phải lựa chọn bảo mật: manifest của Mojang công bố
    sha1, nên muốn đối chiếu thì phải dùng đúng sha1. Bộ soi mã sẽ gắn cờ "hàm băm không an
    toàn" — đổi sang sha256 thì không còn gì để đối chiếu.
    """
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while chunk := handle.read(READ_CHUNK_SIZE):
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


def atomic_write_json(path: Path, document: JsonValue, *, private: bool = False) -> None:
    """Ghi JSON theo kiểu hoặc-được-hoặc-không: file cũ chỉ biến mất khi file mới đã xong.

    Ghi ra file tạm cùng thư mục, `fsync`, rồi `os.replace` — `replace` là nguyên tử trên
    cùng một hệ thống file. Nếu ghi thẳng vào đích, một lần mất điện giữa chừng sẽ để lại
    file cụt mà lần chạy sau đọc vào là hỏng.

    `private=True` đặt quyền 0600, dùng cho file có thể chứa vé đăng nhập.
    """
    ensure_dir(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.chmod(PRIVATE_FILE_MODE if private else DEFAULT_FILE_MODE)
        temporary_path.replace(path)
        sync_directory(path.parent)
    except BaseException:
        # Kể cả khi bị Ctrl-C: không để lại file tạm nằm rác cạnh file thật.
        temporary_path.unlink(missing_ok=True)
        raise


def set_executable(path: Path) -> None:
    """Bật cờ thực thi, giữ nguyên các quyền sẵn có.

    Cần cho `bin/java` sau khi bung JRE của Mojang: manifest có khai cờ thực thi nhưng
    `zipfile` không khôi phục nó, và một JRE không có cờ này thì không chạy được.

    Chỉ bật `x` cho lớp người dùng nào **đã được quyền đọc** — đúng cách `chmod +x` của hệ
    thống làm. Bật `x` cho "other" trên một file mà "other" không đọc được là mở rộng quyền
    ngoài ý muốn.
    """
    mode = path.stat().st_mode
    executable = 0
    for read_bit, execute_bit in (
        (stat.S_IRUSR, stat.S_IXUSR),
        (stat.S_IRGRP, stat.S_IXGRP),
        (stat.S_IROTH, stat.S_IXOTH),
    ):
        if mode & read_bit:
            executable |= execute_bit
    path.chmod(mode | executable)


def sync_directory(directory: Path) -> None:
    """Đẩy thay đổi tên file xuống đĩa thật.

    `os.replace` là nguyên tử, nhưng bản thân việc đổi tên vẫn nằm trong cache của hệ điều
    hành cho tới khi thư mục chứa được fsync. Không có bước này thì mất điện ngay sau khi
    ghi có thể làm file mới biến mất *và* file cũ cũng không còn.

    Windows không cho mở thư mục để fsync — ở đó `os.replace` đã đủ bền vững.
    """
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except (OSError, AttributeError):
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
