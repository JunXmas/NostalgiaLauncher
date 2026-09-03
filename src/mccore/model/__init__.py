"""Các dataclass dùng chung giữa nhiều tầng.

Nằm ở tầng thấp nhất và **không import gì của mccore**. Lý do: `net/download` (L1) phải nhận
`DownloadTask`, còn `install/` (L3) là nơi sinh ra chúng. Nếu kiểu đó định nghĩa trong
`install/` thì L1 buộc phải import L3 — vi phạm luật phụ thuộc ngay ở bước 3.
"""
