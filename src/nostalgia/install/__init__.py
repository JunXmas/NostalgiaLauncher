"""Cài đặt: các module ở đây chỉ **lập kế hoạch**, không tự tải.

Mỗi hàm trả `list[DownloadTask]`; việc tải nằm gọn ở `net/download.py`. Nhờ tách như vậy,
toàn bộ logic cài đặt test được offline — kiểm *danh sách việc sinh ra* thay vì phải tải thật.
"""
