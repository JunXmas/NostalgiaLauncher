"""Keep metadata warnings distinct from explicit current-log failures."""

from nostalgia.api import ModScan


def scan_note(scan: ModScan) -> str:
    errors = sum(finding.severity == "error" for finding in scan.findings)
    warnings = len(scan.findings) - errors
    if errors:
        return f"Log ghi nhận {errors} lỗi; {warnings} cảnh báo/chưa xác minh từ metadata."
    if warnings:
        return (
            f"Có {warnings} cảnh báo/chưa xác minh. Chưa có lỗi được xác nhận từ log; "
            "metadata không kết luận bản chơi không chạy được."
        )
    return "Không có vấn đề thuộc mẫu nhận diện. Kết quả quét không bảo đảm mọi mod tương thích."
