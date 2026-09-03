"""Đo độ song song và tái dùng kết nối khi tải asset từ CDN Mojang.

Dùng `http.client` của thư viện chuẩn — đúng thứ `net/http.py` sẽ dùng, nên số đo ở đây
phản ánh thiết kế thật chứ không phải một thư viện khác.

Không phải test: script in số đo để so với ngân sách trong docs/PERFORMANCE.md. Cần mạng,
và cần một file chỉ mục asset có sẵn trên đĩa để lấy danh sách hash thật.
"""

from __future__ import annotations

import argparse
import http.client
import random
import ssl
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from asset_index import (
    DEFAULT_ASSETS_DIR,
    DEFAULT_INDEX_ID,
    AssetEntry,
    in_band,
    index_path_for,
    load_entries,
    total_bytes,
)

HOST = "resources.download.minecraft.net"
TLS = ssl.create_default_context()
WORKER_COUNTS = (1, 4, 8, 16, 24, 32, 48)


def take_sample(entries: list[AssetEntry], band: str, count: int, seed: int) -> list[AssetEntry]:
    """Lấy mẫu ngẫu nhiên nhưng XÁC ĐỊNH trong một dải, để các lượt đo so được với nhau."""
    chosen = in_band(entries, band)
    random.Random(seed).shuffle(chosen)
    return chosen[:count]


def measure(sample: list[AssetEntry], workers: int, *, reuse: bool) -> float:
    """Tải cả mẫu, trả về số giây. `reuse=False` mở kết nối mới cho từng file."""
    local = threading.local()
    opened: list[http.client.HTTPSConnection] = []
    opened_lock = threading.Lock()

    def connect() -> http.client.HTTPSConnection:
        connection = http.client.HTTPSConnection(HOST, context=TLS, timeout=60)
        with opened_lock:
            opened.append(connection)
        return connection

    def fetch(entry: AssetEntry) -> None:
        path = f"/{entry.object_path.as_posix()}"
        if not reuse:
            connection = connect()
            try:
                connection.request("GET", path)
                connection.getresponse().read()
            finally:
                connection.close()
            return
        connection = getattr(local, "connection", None) or connect()
        local.connection = connection
        try:
            connection.request("GET", path)
            connection.getresponse().read()
        except (http.client.HTTPException, OSError):
            # Kết nối giữ lâu có thể bị phía kia đóng: dựng lại rồi thử một lần nữa.
            connection.close()
            connection = local.connection = connect()
            connection.request("GET", path)
            connection.getresponse().read()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch, sample))
    elapsed = time.perf_counter() - started

    for connection in opened:
        connection.close()
    return elapsed


def median_seconds(sample: list[AssetEntry], workers: int, *, reuse: bool, runs: int) -> float:
    """Trung vị chứ không phải trung bình: một lượt mạng tậm tịt không được kéo lệch số đo."""
    return statistics.median(measure(sample, workers, reuse=reuse) for _ in range(runs))


def warm_up(sample: list[AssetEntry]) -> None:
    """Tải một lượt không tính giờ.

    CDN có cache biên: cấu hình chạy ĐẦU TIÊN sẽ chịu toàn bộ cache miss và trông chậm hơn
    thực tế, làm mọi cấu hình sau đó có vẻ tốt hơn. Hâm nóng trước để loại thiên lệch đó.
    """
    measure(sample, 16, reuse=True)


def sweep_workers(sample: list[AssetEntry], runs: int) -> dict[int, float]:
    """Quét số luồng theo thứ tự NGẪU NHIÊN, để thứ tự chạy không thiên vị cấu hình nào."""
    order = list(WORKER_COUNTS)
    random.Random().shuffle(order)
    return {workers: median_seconds(sample, workers, reuse=True, runs=runs) for workers in order}


def report_sweep(sample: list[AssetEntry], runs: int) -> None:
    print(f"{'độ song song':<16} {'giây':>7} {'file/giây':>11}")
    results = sweep_workers(sample, runs)
    for workers in sorted(results):
        elapsed = results[workers]
        print(f"{workers:>3} luồng      {elapsed:7.2f} {len(sample) / elapsed:11.1f}")


def report_reuse(sample: list[AssetEntry], runs: int) -> None:
    kept = median_seconds(sample, 16, reuse=True, runs=runs)
    fresh = median_seconds(sample, 16, reuse=False, runs=runs)
    print("\ntái dùng kết nối so với mở mới mỗi file, cùng 16 luồng:")
    print(f"  giữ kết nối     {len(sample) / kept:7.1f} file/s")
    print(f"  mở mới mỗi file {len(sample) / fresh:7.1f} file/s")
    print(f"  => giữ kết nối nhanh hơn {fresh / kept:.1f}x")


def report_band(entries: list[AssetEntry], band: str, count: int, seed: int, runs: int) -> None:
    sample = take_sample(entries, band, count, seed)
    megabytes = total_bytes(sample) / 1e6
    print(f"\nmẫu {band}: {len(sample)} file, {megabytes:.1f} MB")
    warm_up(sample)
    for workers in (8, 16, 24):
        elapsed = median_seconds(sample, workers, reuse=True, runs=runs)
        rate = len(sample) / elapsed
        speed = megabytes / elapsed
        print(f"{workers:>3} luồng: {elapsed:6.2f} s -> {rate:6.1f} file/s, {speed:5.1f} MB/s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS_DIR)
    parser.add_argument("--index-id", default=DEFAULT_INDEX_ID)
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--runs", type=int, default=3, help="số lượt mỗi cấu hình, lấy trung vị")
    args = parser.parse_args()

    index_path = index_path_for(args.assets, args.index_id)
    if not index_path.exists():
        print(f"không tìm thấy chỉ mục asset: {index_path}")
        return 1
    if args.count < 1 or args.runs < 1:
        # Mẫu rỗng vẫn chạy trót lọt và in ra 0,0 file/s — số vô nghĩa mà trông như số đo.
        print("--count và --runs phải >= 1")
        return 2

    entries, _raw_count = load_entries(index_path)
    small = take_sample(entries, "nhỏ (<16 KB)", args.count, seed=7)
    print(f"mẫu file nhỏ: {len(small)} file, {total_bytes(small) / 1024:.0f} KB")
    print(f"hâm nóng CDN một lượt, rồi trung vị {args.runs} lượt mỗi cấu hình\n")

    warm_up(small)
    report_sweep(small, args.runs)
    report_reuse(small, args.runs)
    report_band(entries, "vừa (16-64 KB)", count=60, seed=11, runs=max(1, args.runs - 1))
    report_band(entries, "lớn (>=64 KB)", count=24, seed=13, runs=max(1, args.runs - 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
