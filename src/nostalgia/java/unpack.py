"""Dựng bản Java trên đĩa: thư mục, bung nén, liên kết, cờ thực thi.

**Vì sao bung lzma ở đây chứ không thêm cờ vào `net/download.py`.** Mojang cung cấp bản nén
lzma cho phần lớn file trong bản Java, và chỉ ở đó — không có ở client.jar, thư viện hay
asset. Đo trên bản thật: `jre-legacy/linux` tải 223 MB nếu lấy bản thô, 51 MB nếu lấy bản
nén (giảm 77%). Trên đường truyền 5 MB/s đó là 47 giây rút còn khoảng 13. Nhét chuyện này
vào bộ tải chung sẽ bắt mọi lời gọi khác mang theo một cờ luôn tắt.

`lzma.LZMADecompressor.decompress` **nhả GIL**, nên bung song song thật sự có tác dụng: đo
được 8 luồng nhanh gấp đôi một luồng (43 MB/s).
"""

from __future__ import annotations

import hashlib
import lzma
import os
import tempfile
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nostalgia.errors import IntegrityError
from nostalgia.java.runtime_plan import CompressedFile, RuntimeLink
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress
from nostalgia.storage.files import DEFAULT_FILE_MODE, ensure_dir, set_executable, sync_directory

# Mojang dùng container LZMA "alone" (không phải .xz). Ghi rõ thay vì để `FORMAT_AUTO` đoán:
# nếu một ngày họ đổi định dạng, ta muốn thấy lỗi ngay chứ không âm thầm nhận thứ khác.
LZMA_FORMAT = lzma.FORMAT_ALONE
CHUNK_BYTES = 1 << 18
STAGE = "bung"

# Ít luồng hơn bộ tải (16) vì đây là việc nặng CPU chứ không phải chờ mạng. Đo được 8 luồng
# nhanh gấp đôi một luồng và sau đó không cải thiện thêm — số lõi thật của máy phổ thông.
DEFAULT_DECODE_WORKERS = 8


def create_directories(directories: Sequence[Path]) -> None:
    """Tạo trước mọi thư mục manifest khai.

    Phải chạy trước bước tải: manifest khai cả thư mục **rỗng** (đo thật: 88 thư mục cho
    `jre-legacy`), mà thư mục rỗng thì không file nào tạo hộ.
    """
    for directory in directories:
        ensure_dir(directory)


def decode_compressed(
    archives: Sequence[CompressedFile],
    *,
    workers: int = DEFAULT_DECODE_WORKERS,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
) -> int:
    """Bung từng file nén ra đích thật, xác minh sha1 bản thô, rồi xoá file nén.

    Trả về tổng số byte đã ghi. Lỗi ở một file làm hỏng cả lượt — khác với lúc tải, vì tới
    đây byte đã nằm trên đĩa và một file Java hỏng nghĩa là bản Java không chạy được.
    """
    if not archives:
        return 0
    done = 0
    on_progress(Progress(STAGE, done, len(archives)))
    written_total = 0
    with ThreadPoolExecutor(max_workers=min(workers, len(archives))) as pool:
        for written in pool.map(lambda archive: _decode_one(archive, cancel_token), archives):
            written_total += written
            done += 1
            on_progress(Progress(STAGE, done, len(archives)))
    return written_total


def create_links(links: Sequence[RuntimeLink]) -> None:
    """Tạo liên kết tượng trưng; chép file khi hệ thống không cho tạo.

    Windows đòi quyền riêng mới cho tạo symlink, nên `OSError` ở đây là chuyện bình thường
    chứ không phải lỗi lập trình. Chép là đường lùi đúng: bản Java chỉ cần nội dung.
    """
    for link in links:
        if link.link_path.is_symlink() or link.link_path.exists():
            continue
        ensure_dir(link.link_path.parent)
        try:
            link.link_path.symlink_to(link.target)
        except OSError:
            _copy_file(link.resolved_target, link.link_path)


def apply_executable_bits(paths: Sequence[Path]) -> None:
    """Bật cờ thực thi cho những file manifest khai là chạy được.

    Chạy lại vô hại, nên gọi cả với file đã có sẵn từ lần cài trước — một bản Java thiếu cờ
    này im lặng không chạy, và đó là lỗi rất khó lần ra.
    """
    for path in paths:
        if path.exists():
            set_executable(path)


def _decode_one(archive: CompressedFile, cancel_token: CancelToken | None) -> int:
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    ensure_dir(archive.destination.parent)
    decompressor = lzma.LZMADecompressor(format=LZMA_FORMAT)
    digest = hashlib.sha1()
    descriptor, temporary_name = tempfile.mkstemp(
        dir=archive.destination.parent, prefix=f".{archive.destination.name}."
    )
    temporary_path = Path(temporary_name)
    written = 0
    try:
        with archive.archive_path.open("rb") as source, os.fdopen(descriptor, "wb") as sink:
            while chunk := source.read(CHUNK_BYTES):
                # Kiểm sau MỖI khối, đúng như bộ tải: file lớn nhất trong một bản Java là
                # `lib/modules` cỡ 130 MB, kiểm một lần ở đầu thì nút dừng vô dụng với nó.
                if cancel_token is not None:
                    cancel_token.raise_if_cancelled()
                block = decompressor.decompress(chunk)
                if block:
                    digest.update(block)
                    sink.write(block)
                    written += len(block)
            sink.flush()
            os.fsync(sink.fileno())
        _verify(archive, written, digest.hexdigest())
        temporary_path.chmod(DEFAULT_FILE_MODE)
        temporary_path.replace(archive.destination)
        sync_directory(archive.destination.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    archive.archive_path.unlink(missing_ok=True)
    return written


def _verify(archive: CompressedFile, written: int, actual_sha1: str) -> None:
    if archive.size is not None and written != archive.size:
        message = (
            f"{archive.destination.name}: bung ra {written} byte, manifest khai {archive.size}"
        )
        raise IntegrityError(message)
    if archive.sha1 is not None and actual_sha1 != archive.sha1:
        message = f"{archive.destination.name}: sha1 {actual_sha1}, manifest khai {archive.sha1}"
        raise IntegrityError(message)


def _copy_file(source: Path, destination: Path) -> None:
    """Chép qua file tạm rồi đổi tên: bản chép dở dang của `bin/java` không ai bắt được.

    Khác các file tải về, bản chép này không nằm trong danh sách xác minh nào — nếu đứt
    gánh giữa chừng thì lần chạy sau vẫn thấy "đã có file" và bỏ qua.
    """
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}."
    )
    temporary_path = Path(temporary_name)
    try:
        with source.open("rb") as reader, os.fdopen(descriptor, "wb") as writer:
            while chunk := reader.read(CHUNK_BYTES):
                writer.write(chunk)
        temporary_path.chmod(source.stat().st_mode & 0o777)
        temporary_path.replace(destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
