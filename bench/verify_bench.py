"""So chi phí xác minh bản cài bằng kích thước với bằng sha1.

Không phải test: script in số đo để so với ngân sách trong docs/PERFORMANCE.md.
Không cần mạng, nhưng cần asset đã tải sẵn trên đĩa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".nostalgia-launcher" / "assets"
CHUNK = 1 << 20


def sha1_of_file(path: Path) -> tuple[str, int]:
    """Trả về (sha1, số byte đọc thật). Đếm byte thật để MB/s không sai khi file cụt."""
    digest = hashlib.sha1()
    read_bytes = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
            read_bytes += len(chunk)
    return digest.hexdigest(), read_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--index-id", default="5")
    args = parser.parse_args()

    index_path = args.assets / "indexes" / f"{args.index_id}.json"
    objects_dir = args.assets / "objects"
    if not index_path.exists():
        print(f"không tìm thấy chỉ mục: {index_path}")
        return 1

    objects = json.loads(index_path.read_text(encoding="utf-8"))["objects"]
    unique = {v["hash"]: v["size"] for v in objects.values()}
    print(f"chỉ mục {args.index_id}: {len(objects)} mục, {len(unique)} hash duy nhất")
    print(f"  -> {len(objects) - len(unique)} mục trùng hash bị loại khi dedupe")

    sizes = sorted(unique.values())
    total = sum(sizes)
    print(f"  tổng {total / 1e6:.0f} MB, trung vị {statistics.median(sizes) / 1024:.1f} KB")
    bands = [
        ("< 16 KB", 0, 16 * 1024),
        ("16-64 KB", 16 * 1024, 64 * 1024),
        (">= 64 KB", 64 * 1024, 1 << 40),
    ]
    for label, low, high in bands:
        chosen = [s for s in sizes if low <= s < high]
        print(f"  {label:<9}: {len(chosen):5d} file, {sum(chosen) / 1e6:6.1f} MB")

    # KHÔNG lọc trước bằng .exists(): làm thế là stat sẵn toàn bộ file, hâm nóng cache
    # metadata, và phép đo bên dưới sẽ luôn ra số của đĩa nóng. Gộp việc kiểm tồn tại
    # vào chính vòng đo.
    started = time.perf_counter()
    matched = missing = 0
    for asset_hash, size in unique.items():
        try:
            if (objects_dir / asset_hash[:2] / asset_hash).stat().st_size == size:
                matched += 1
        except FileNotFoundError:
            missing += 1
    stat_seconds = time.perf_counter() - started
    print(f"chỉ stat  : {stat_seconds * 1000:8.1f} ms ({matched} khớp, {missing} thiếu)")
    print("  (lượt đầu sau khi bật máy sẽ chậm hơn: đây là số trên cache metadata đã nóng)")

    present = [(h, s) for h, s in unique.items() if (objects_dir / h[:2] / h).exists()]
    if not present:
        return 1

    started = time.perf_counter()
    hashed_bytes = 0
    for asset_hash, _size in present:
        _digest, read_bytes = sha1_of_file(objects_dir / asset_hash[:2] / asset_hash)
        hashed_bytes += read_bytes
    sha1_seconds = time.perf_counter() - started
    print(
        f"sha1 toàn bộ: {sha1_seconds:6.2f} s "
        f"({hashed_bytes / 1e6:.0f} MB, {hashed_bytes / 1e6 / sha1_seconds:.0f} MB/s)"
    )
    print(f"=> sha1 chậm hơn stat {sha1_seconds / stat_seconds:.0f} lần")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
