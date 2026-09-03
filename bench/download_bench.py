"""Đo độ song song và tái dùng kết nối khi tải asset từ CDN Mojang.

Dùng `http.client` của thư viện chuẩn — đúng thứ `net/http.py` sẽ dùng, nên số đo ở đây
phản ánh thiết kế thật chứ không phải một thư viện khác.

Không phải test: script in số đo để người đọc so với ngân sách trong docs/PERFORMANCE.md.
Cần mạng, và cần một file chỉ mục asset có sẵn trên đĩa để lấy danh sách hash thật.
"""

from __future__ import annotations

import argparse
import http.client
import json
import random
import ssl
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HOST = "resources.download.minecraft.net"
DEFAULT_INDEX = Path.home() / ".nostalgia-launcher" / "assets" / "indexes" / "5.json"
SMALL_LIMIT = 16 * 1024  # "file nhỏ": nhóm bị chi phối bởi số vòng request
LARGE_LIMIT = 64 * 1024  # "file lớn": nhóm bị chi phối bởi băng thông
TLS = ssl.create_default_context()

# Ba dải kích thước, đặt tên đúng như bảng phân bố mà verify_bench.py in ra.
BANDS = {
    "nhỏ (<16 KB)": (0, SMALL_LIMIT),
    "vừa (16-64 KB)": (SMALL_LIMIT, LARGE_LIMIT),
    "lớn (>=64 KB)": (LARGE_LIMIT, 1 << 40),
}


def load_sample(index_path: Path, count: int, band: str) -> list[tuple[str, int]]:
    """Lấy mẫu hash duy nhất trong một dải kích thước.

    Ba dải phủ kín chỉ mục, không chồng lấn: nhóm nhỏ đo chi phí mỗi vòng request, nhóm
    lớn đo băng thông, nhóm vừa là phần đông nhất theo số file nên không được bỏ qua —
    ước tính thời gian cài mà thiếu nó là ngoại suy chứ không phải đo.
    """
    low, high = BANDS[band]
    objects = json.loads(index_path.read_text(encoding="utf-8"))["objects"]
    unique = {v["hash"]: v["size"] for v in objects.values()}
    picked = [(h, s) for h, s in sorted(unique.items()) if low <= s < high]
    random.Random(7).shuffle(picked)
    return picked[:count]


def measure(sample: list[tuple[str, int]], workers: int, *, reuse: bool) -> float:
    """Tải cả mẫu, trả về số giây. `reuse=False` mở kết nối mới cho từng file."""
    local = threading.local()
    opened: list[http.client.HTTPSConnection] = []
    opened_lock = threading.Lock()

    def connect() -> http.client.HTTPSConnection:
        conn = http.client.HTTPSConnection(HOST, context=TLS, timeout=60)
        with opened_lock:
            opened.append(conn)
        return conn

    def fetch_one(item: tuple[str, int]) -> None:
        asset_hash, _ = item
        path = f"/{asset_hash[:2]}/{asset_hash}"
        if not reuse:
            conn = connect()
            try:
                conn.request("GET", path)
                conn.getresponse().read()
            finally:
                conn.close()
            return
        conn = getattr(local, "conn", None) or connect()
        local.conn = conn
        try:
            conn.request("GET", path)
            conn.getresponse().read()
        except (http.client.HTTPException, OSError):
            # Kết nối giữ lâu có thể bị phía kia đóng: dựng lại rồi thử một lần nữa.
            conn.close()
            conn = local.conn = connect()
            conn.request("GET", path)
            conn.getresponse().read()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch_one, sample))
    elapsed = time.perf_counter() - started

    for conn in opened:
        conn.close()
    return elapsed


def median_of(sample: list[tuple[str, int]], workers: int, *, reuse: bool, runs: int) -> float:
    """Trung vị chứ không phải trung bình: một lượt mạng tậm tịt không được kéo lệch cả số đo."""
    return statistics.median(measure(sample, workers, reuse=reuse) for _ in range(runs))


def warm_up(sample: list[tuple[str, int]]) -> None:
    """Tải một lượt không tính giờ.

    CDN có cache biên: cấu hình chạy ĐẦU TIÊN sẽ chịu toàn bộ cache miss và trông chậm
    hơn thực tế, làm mọi cấu hình sau đó có vẻ tốt hơn. Hâm nóng trước để loại thiên lệch
    đó, thay vì để nó âm thầm thổi phồng lợi ích của việc tăng số luồng.
    """
    measure(sample, 16, reuse=True)


def sweep(sample: list[tuple[str, int]], workers_list: list[int], runs: int) -> dict[int, float]:
    """Quét số luồng theo thứ tự NGẪU NHIÊN, để thứ tự chạy không thiên vị cấu hình nào."""
    order = list(workers_list)
    random.Random().shuffle(order)
    return {w: median_of(sample, w, reuse=True, runs=runs) for w in order}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--runs", type=int, default=3, help="số lượt mỗi cấu hình, lấy trung vị")
    args = parser.parse_args()

    if not args.index.exists():
        print(f"không tìm thấy chỉ mục asset: {args.index}")
        return 1
    if args.count < 1 or args.runs < 1:
        # Mẫu rỗng vẫn chạy trót lọt và in ra 0,0 file/s — số vô nghĩa mà trông như số đo.
        print("--count và --runs phải >= 1")
        return 2

    small = load_sample(args.index, args.count, "nhỏ (<16 KB)")
    print(f"mẫu file nhỏ: {len(small)} file, {sum(s for _, s in small) / 1024:.0f} KB")
    print(f"hâm nóng CDN một lượt, rồi trung vị {args.runs} lượt mỗi cấu hình\n")
    warm_up(small)

    print(f"{'độ song song':<16} {'giây':>7} {'file/giây':>11}")
    results = sweep(small, [1, 4, 8, 16, 24, 32, 48], args.runs)
    for workers in sorted(results):
        elapsed = results[workers]
        print(f"{workers:>3} luồng      {elapsed:7.2f} {len(small) / elapsed:11.1f}")

    print("\ntái dùng kết nối so với mở mới mỗi file, cùng 16 luồng:")
    kept = median_of(small, 16, reuse=True, runs=args.runs)
    fresh = median_of(small, 16, reuse=False, runs=args.runs)
    print(f"  giữ kết nối     {len(small) / kept:7.1f} file/s")
    print(f"  mở mới mỗi file {len(small) / fresh:7.1f} file/s")
    print(f"  => giữ kết nối nhanh hơn {fresh / kept:.1f}x")

    for band, count in (("vừa (16-64 KB)", 60), ("lớn (>=64 KB)", 24)):
        sample = load_sample(args.index, count, band)
        megabytes = sum(size for _, size in sample) / 1e6
        print(f"\nmẫu {band}: {len(sample)} file, {megabytes:.1f} MB")
        warm_up(sample)
        for workers in (8, 16, 24):
            elapsed = median_of(sample, workers, reuse=True, runs=max(1, args.runs - 1))
            rate = len(sample) / elapsed
            speed = megabytes / elapsed
            print(f"{workers:>3} luồng: {elapsed:6.2f} s -> {rate:6.1f} file/s, {speed:5.1f} MB/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
