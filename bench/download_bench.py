"""Đo ảnh hưởng của độ song song và tái dùng kết nối khi tải asset từ CDN Mojang.

Không phải test: script in số đo để người đọc so với ngân sách trong docs/PERFORMANCE.md.
Cần mạng, và cần một file chỉ mục asset có sẵn trên đĩa để lấy danh sách hash thật.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter

CDN = "https://resources.download.minecraft.net"
DEFAULT_INDEX = Path.home() / ".nostalgia-launcher" / "assets" / "indexes" / "5.json"
SMALL_LIMIT = 16 * 1024  # "file nhỏ": nhóm bị chi phối bởi số vòng request
LARGE_LIMIT = 64 * 1024  # "file lớn": nhóm bị chi phối bởi băng thông


def load_sample(index_path: Path, count: int, *, small: bool) -> list[tuple[str, int]]:
    """Lấy mẫu hash duy nhất từ chỉ mục asset.

    Hai nhóm được tách hẳn bằng hai ngưỡng khác nhau, không dùng chung một mốc: nhóm nhỏ là
    < 16 KB (đo chi phí mỗi vòng request), nhóm lớn là >= 64 KB (đo băng thông). Khoảng giữa
    bị bỏ qua có chủ ý để hai phép đo không lẫn vào nhau.
    """
    objects = json.loads(index_path.read_text(encoding="utf-8"))["objects"]
    unique = {v["hash"]: v["size"] for v in objects.values()}
    keep = (lambda size: size < SMALL_LIMIT) if small else (lambda size: size >= LARGE_LIMIT)
    picked = [(h, s) for h, s in sorted(unique.items()) if keep(s)]
    random.Random(7 if small else 11).shuffle(picked)
    return picked[:count]


def measure(sample: list[tuple[str, int]], workers: int, *, pooled: bool) -> float:
    """Tải cả mẫu vào thư mục tạm, trả về số giây."""
    target = Path(tempfile.mkdtemp())
    session = requests.Session()
    session.mount("https://", HTTPAdapter(pool_connections=workers, pool_maxsize=workers))

    def fetch_one(item: tuple[str, int]) -> None:
        asset_hash, _ = item
        url = f"{CDN}/{asset_hash[:2]}/{asset_hash}"
        get = session.get if pooled else requests.get
        with get(url, timeout=60, stream=True) as response:
            response.raise_for_status()
            with (target / asset_hash).open("wb") as handle:
                for chunk in response.iter_content(1 << 16):
                    handle.write(chunk)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch_one, sample))
    elapsed = time.perf_counter() - started

    session.close()
    shutil.rmtree(target, ignore_errors=True)
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--count", type=int, default=120)
    args = parser.parse_args()

    if not args.index.exists():
        print(f"không tìm thấy chỉ mục asset: {args.index}")
        return 1

    small = load_sample(args.index, args.count, small=True)
    total_kb = sum(size for _, size in small) / 1024
    print(f"mẫu file nhỏ: {len(small)} file, {total_kb:.0f} KB")
    print(f"{'cấu hình':<30} {'giây':>7} {'file/giây':>10}")
    for workers, pooled in [(1, True), (4, True), (8, True), (16, True), (32, True), (16, False)]:
        elapsed = measure(small, workers, pooled=pooled)
        label = f"{workers:2d} luồng, {'dùng lại kết nối' if pooled else 'kết nối mới mỗi file'}"
        print(f"{label:<30} {elapsed:7.2f} {len(small) / elapsed:10.1f}")

    big = load_sample(args.index, 24, small=False)
    total_mb = sum(size for _, size in big) / 1e6
    print(f"\nmẫu file lớn: {len(big)} file, {total_mb:.1f} MB")
    for workers in (4, 8, 16):
        elapsed = measure(big, workers, pooled=True)
        print(f"{workers:2d} luồng: {elapsed:6.2f} s -> {total_mb / elapsed:6.1f} MB/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
