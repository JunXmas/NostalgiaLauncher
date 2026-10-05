"""Giải nén thư viện natives vào thư mục để JVM nạp.

**Làm phẳng có chủ ý.** Soi jar thật: `jtracy` để `.so` ngay ở gốc, còn `lwjgl-vma` chôn nó
dưới `linux/x64/org/lwjgl/vma/`. JVM **không tìm đệ quy** trong `java.library.path`, nên giữ
nguyên cây thư mục là game không nạp được thư viện. Đã đo trên ba phiên bản (1.8.9, 1.20.1,
1.21.4): làm phẳng không gây đụng tên nào — nhưng nếu có đụng (đã gặp thật với freetype.dll
trên một số phiên bản), giữ bản lớn hơn và ghi log cảnh báo.

Hai lớp chặn tài nguyên: trần tổng dung lượng giải nén, và bỏ qua mục là symlink trong
archive. Cả hai đều là chuyện của archive tải từ mạng.
"""

from __future__ import annotations

import logging
import stat
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import IntegrityError, UnsafePathError
from nostalgia.install.library import NativeArchive
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import ensure_dir, resolve_child

log = logging.getLogger(__name__)

# Trần cho tổng dung lượng bung ra từ MỘT lượt giải nén. Đo thật: 1.20.1 bung 18 file, dưới
# 20 MB. 512 MiB là rất thoáng; điều quan trọng là có trần, vì một archive dựng ác ý có thể
# khai dung lượng bung khổng lồ ("zip bomb").
DEFAULT_MAX_EXTRACTED_BYTES = 512 * 1024 * 1024

# Luôn bỏ, bất kể version JSON khai gì. Mojang CHỈ khai `extract.exclude` cho natives đời cũ;
# thư viện natives đời >=1.19 không khai gì cả, nên nếu chỉ nghe theo khai báo thì
# `META-INF/MANIFEST.MF` bị bung từ MỌI jar và đụng nhau ngay. Đã gặp thật khi chạy trên jar
# thật của 1.21.4. META-INF không bao giờ chứa thư viện natives.
ALWAYS_EXCLUDED = ("META-INF/",)


@dataclass(frozen=True, slots=True)
class ExtractionReport:
    """Đã bung ra những file nào, và bỏ qua bao nhiêu file vì đã đúng sẵn."""

    extracted: tuple[Path, ...]
    skipped_unchanged: int
    total_bytes: int


def iter_native_targets(archives: tuple[NativeArchive, ...]) -> Iterator[tuple[str, int]]:
    """Những file mà việc giải nén SẼ tạo ra: (tên đã làm phẳng, kích thước).

    Có mặt để `doctor` biết phải tìm gì mà không phải chép lại luật lọc và luật làm phẳng.
    Chép lại là cách chắc chắn để một ngày nào đó hai chỗ hiểu khác nhau và `doctor` báo
    thiếu một file vốn không bao giờ được tạo ra.
    """
    for archive in archives:
        with zipfile.ZipFile(archive.archive_path) as opened:
            for member in opened.infolist():
                if not _should_extract(member, (*ALWAYS_EXCLUDED, *archive.excludes)):
                    continue
                name = Path(member.filename).name
                if name:
                    yield name, member.file_size


def extract_natives(
    archives: tuple[NativeArchive, ...],
    natives_dir: Path,
    *,
    max_extracted_bytes: int = DEFAULT_MAX_EXTRACTED_BYTES,
    cancel_token: CancelToken | None = None,
) -> ExtractionReport:
    """Bung mọi archive vào `natives_dir`, làm phẳng tên file.

    Chạy lại lần hai gần như không làm gì: file đã đúng kích thước thì bỏ qua, đúng theo
    luật "xác minh bằng kích thước" dùng ở mọi nơi khác trong kho.
    """
    ensure_dir(natives_dir)
    extracted: list[Path] = []
    skipped = 0
    written_bytes = 0

    for archive in archives:
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        with zipfile.ZipFile(archive.archive_path) as opened:
            for member in opened.infolist():
                if not _should_extract(member, (*ALWAYS_EXCLUDED, *archive.excludes)):
                    continue
                target = _flattened_target(natives_dir, member.filename)
                if target is None:
                    continue
                written_bytes += member.file_size
                if written_bytes > max_extracted_bytes:
                    message = (
                        f"{archive.archive_path.name}: bung quá {max_extracted_bytes} byte, đã ngắt"
                    )
                    raise IntegrityError(message)
                if _already_extracted(target, member):
                    skipped += 1
                    continue
                _write_member(opened, member, target)
                extracted.append(target)

    return ExtractionReport(
        extracted=tuple(extracted), skipped_unchanged=skipped, total_bytes=written_bytes
    )


def _should_extract(member: zipfile.ZipInfo, excludes: tuple[str, ...]) -> bool:
    if member.is_dir():
        return False
    if any(member.filename.startswith(prefix) for prefix in excludes):
        return False
    # Symlink trong archive: Python ghi ra một file chứa đường dẫn đích chứ không tạo liên
    # kết, nên không nguy hiểm trực tiếp — nhưng nó là rác, và một liên kết trỏ ra ngoài là
    # thứ không nên chiều theo.
    return not stat.S_ISLNK(member.external_attr >> 16)


def _flattened_target(natives_dir: Path, member_name: str) -> Path | None:
    """Chỉ lấy phần tên file. Trả `None` nếu tên rỗng sau khi làm phẳng."""
    name = Path(member_name).name
    if not name:
        return None
    try:
        return resolve_child(natives_dir, name)
    except UnsafePathError:
        return None


def _already_extracted(target: Path, member: zipfile.ZipInfo) -> bool:
    try:
        return target.stat().st_size == member.file_size
    except FileNotFoundError:
        return False


def _write_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo, target: Path) -> None:
    """Ghi một mục ra đĩa; nếu hai archive khác nhau cùng đòi một tên, giữ bản lớn hơn.

    Làm phẳng khiến hai file khác thư mục có thể trùng tên. Đo trên ba phiên bản thì không
    xảy ra, nhưng trên thực tế LWJGL-freetype có thể đóng `freetype.dll` với kích thước khác
    nhau giữa hai JAR. Ghi đè lặng lẽ là cách tệ nhất: game nạp nhầm thư viện và lỗi hiện
    ra ở chỗ khác. Giữ bản lớn hơn (thường là bản đầy đủ hơn) và ghi cảnh báo.
    """
    if target.exists():
        existing_size = target.stat().st_size
        if existing_size != member.file_size:
            log.warning(
                "natives trùng tên %r: đã có %d byte, archive đưa %d byte — giữ bản lớn hơn",
                target.name,
                existing_size,
                member.file_size,
            )
            if member.file_size <= existing_size:
                return  # bản đang có lớn hơn hoặc bằng, bỏ qua bản mới
            # bản mới lớn hơn → ghi đè bên dưới
    with archive.open(member) as source, target.open("wb") as sink:
        while chunk := source.read(1 << 18):
            sink.write(chunk)
