"""So chi phí xác minh bản cài bằng kích thước với bằng sha1.

Không phải test: script in số đo để so với ngân sách trong docs/PERFORMANCE.md.
Không cần mạng, nhưng cần asset đã tải sẵn trên đĩa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".nostalgia-launcher" / "assets"
CHUNK = 1 << 20


def sha1_of_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


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

    present = [(h, s) for h, s in unique.items() if (objects_dir / h[:2] / h).exists()]
    print(f"có mặt trên đĩa: {len(present)}/{len(unique)}")
    if not present:
        return 1

    started = time.perf_counter()
    matched = sum(1 for h, s in present if (objects_dir / h[:2] / h).stat().st_size == s)
    stat_seconds = time.perf_counter() - started
    print(f"chỉ stat  : {stat_seconds * 1000:8.1f} ms ({matched} file khớp kích thước)")

    started = time.perf_counter()
    hashed_bytes = 0
    for asset_hash, size in present:
        sha1_of_file(objects_dir / asset_hash[:2] / asset_hash)
        hashed_bytes += size
    sha1_seconds = time.perf_counter() - started
    print(
        f"sha1 toàn bộ: {sha1_seconds:6.2f} s "
        f"({hashed_bytes / 1e6:.0f} MB, {hashed_bytes / 1e6 / sha1_seconds:.0f} MB/s)"
    )
    print(f"=> sha1 chậm hơn stat {sha1_seconds / stat_seconds:.0f} lần")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
