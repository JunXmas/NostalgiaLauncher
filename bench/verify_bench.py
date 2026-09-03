"""So chi phí xác minh bản cài bằng kích thước với bằng sha1, và in phân bố kích thước.

Không phải test: script in số đo để so với ngân sách trong docs/PERFORMANCE.md.
Không cần mạng, nhưng cần asset đã tải sẵn trên đĩa.
"""

from __future__ import annotations

import argparse
import hashlib
import statistics
import time
from pathlib import Path

from asset_index import (
    BANDS,
    DEFAULT_ASSETS_DIR,
    DEFAULT_INDEX_ID,
    AssetEntry,
    in_band,
    index_path_for,
    load_entries,
    total_bytes,
)

READ_CHUNK = 1 << 20


def sha1_of_file(path: Path) -> tuple[str, int]:
    """Trả về (sha1, số byte đọc thật).

    Đếm byte thật chứ không lấy kích thước theo chỉ mục, để MB/s không bị thổi lên khi gặp
    file cụt.

    sha1 ở đây là ràng buộc giao thức, không phải lựa chọn bảo mật: manifest của Mojang công
    bố sha1 nên muốn đối chiếu thì phải dùng đúng sha1. Bộ soi mã sẽ gắn cờ "hàm băm không
    an toàn" — đừng đổi sang sha256, sẽ không đối chiếu được với gì cả.
    """
    digest = hashlib.sha1()
    read_bytes = 0
    with path.open("rb") as handle:
        while chunk := handle.read(READ_CHUNK):
            digest.update(chunk)
            read_bytes += len(chunk)
    return digest.hexdigest(), read_bytes


def print_distribution(entries: list[AssetEntry], raw_count: int) -> None:
    sizes = sorted(entry.size for entry in entries)
    print(f"chỉ mục: {raw_count} mục, {len(entries)} hash duy nhất")
    print(f"  -> {raw_count - len(entries)} mục trùng hash bị loại khi dedupe")
    megabytes = total_bytes(entries) / 1e6
    median_kb = statistics.median(sizes) / 1024
    print(f"  tổng {megabytes:.0f} MB, trung vị {median_kb:.1f} KB")
    for band in BANDS:
        chosen = in_band(entries, band)
        print(f"  {band:<16}: {len(chosen):5d} file, {total_bytes(chosen) / 1e6:6.1f} MB")


def measure_stat(entries: list[AssetEntry], objects_dir: Path) -> tuple[float, int, int]:
    """Xác minh bằng kích thước.

    KHÔNG lọc trước bằng `.exists()`: làm thế là stat sẵn toàn bộ file, hâm nóng cache
    metadata, và phép đo sẽ luôn ra số của đĩa nóng. Việc kiểm tồn tại nằm trong chính
    vòng đo.
    """
    started = time.perf_counter()
    matched = missing = 0
    for entry in entries:
        try:
            if (objects_dir / entry.object_path).stat().st_size == entry.size:
                matched += 1
        except FileNotFoundError:
            missing += 1
    return time.perf_counter() - started, matched, missing


def measure_sha1(entries: list[AssetEntry], objects_dir: Path) -> tuple[float, int]:
    started = time.perf_counter()
    hashed_bytes = 0
    for entry in entries:
        path = objects_dir / entry.object_path
        if path.exists():
            _digest, read_bytes = sha1_of_file(path)
            hashed_bytes += read_bytes
    return time.perf_counter() - started, hashed_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS_DIR)
    parser.add_argument("--index-id", default=DEFAULT_INDEX_ID)
    args = parser.parse_args()

    index_path = index_path_for(args.assets, args.index_id)
    if not index_path.exists():
        print(f"không tìm thấy chỉ mục: {index_path}")
        return 1

    entries, raw_count = load_entries(index_path)
    print_distribution(entries, raw_count)

    objects_dir = args.assets / "objects"
    stat_seconds, matched, missing = measure_stat(entries, objects_dir)
    print(f"chỉ stat    : {stat_seconds * 1000:8.1f} ms ({matched} khớp, {missing} thiếu)")
    print("  (lượt đầu sau khi bật máy sẽ chậm hơn: đây là số trên cache metadata đã nóng)")

    sha1_seconds, hashed_bytes = measure_sha1(entries, objects_dir)
    if not hashed_bytes:
        print("không có file nào trên đĩa để băm")
        return 1
    speed = hashed_bytes / 1e6 / sha1_seconds
    print(f"sha1 toàn bộ: {sha1_seconds:8.2f} s ({hashed_bytes / 1e6:.0f} MB, {speed:.0f} MB/s)")
    print(f"=> sha1 chậm hơn stat {sha1_seconds / stat_seconds:.0f} lần")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
