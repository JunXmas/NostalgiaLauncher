"""Xác minh chứng chỉ TLS bằng bộ xác minh của hệ điều hành (qua `truststore`, nếu có)."""

from __future__ import annotations

import ssl
import threading

_TLS_LOCK = threading.Lock()
_TLS_CACHE: dict[str, ssl.SSLContext] = {}


def default_tls_context() -> ssl.SSLContext:
    """Context TLS mặc định dùng chung cho cả tiến trình, tạo MỘT lần dưới khoá.

    Nạp chứng chỉ hệ thống (`load_default_certs`) song song từ nhiều luồng từng làm CPython
    segfault trên CI: lúc mở cửa sổ, vài cầu nối cùng dựng `HttpClient` trong luồng nền. Một
    `SSLContext` dùng chung sau khi tạo là an toàn, và khỏi đọc lại kho chứng chỉ mỗi lần.
    """
    with _TLS_LOCK:
        if "default" not in _TLS_CACHE:
            _TLS_CACHE["default"] = system_verifier_context() or ssl.create_default_context()
        return _TLS_CACHE["default"]


def system_verifier_context() -> ssl.SSLContext | None:
    """Context xác minh chứng chỉ bằng bộ xác minh CỦA HỆ ĐIỀU HÀNH, nếu có `truststore`.

    Vì sao cần: trên Windows, `ssl.create_default_context()` chỉ chép những root ĐANG nằm sẵn
    trong kho chứng chỉ vào OpenSSL. Windows không giữ đủ root trong kho — nó tải root (và
    intermediate còn thiếu) từ Windows Update vào đúng lúc Schannel cần. Máy Windows 10 lâu
    không cập nhật vì vậy thiếu root mà CDN đang dùng: `curl.exe` (Schannel) vào được
    cdn.modrinth.com, còn launcher hỏng TLS ngay lúc bắt tay và người dùng chỉ thấy "thất
    bại sau 4 lần thử: không gọi được https://cdn.modrinth.com/...". `truststore` giao việc
    xác minh cho Schannel / Security.framework / OpenSSL hệ thống — y như trình duyệt và curl.

    Không có `truststore` (chạy lõi từ mã nguồn không kèm `ui`) thì trả None và dùng `ssl`
    chuẩn như cũ: lõi vẫn không có phụ thuộc runtime bắt buộc.
    """
    try:
        import truststore  # tuỳ chọn: chỉ có khi cài kèm gói `ui`
    except ImportError:
        return None
    try:
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except (OSError, ssl.SSLError, RuntimeError):
        return None
