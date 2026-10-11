"""Lỗi chứng chỉ dễ đọc; giữ nguyên lỗi gốc để chẩn đoán, không nới xác minh TLS."""

from __future__ import annotations

import logging
import ssl

from nostalgia.errors import NetworkError

logger = logging.getLogger(__name__)


def certificate_failure(host: str, error: ssl.SSLCertVerificationError) -> NetworkError:
    """OpenSSL và Windows dùng mã khác nhau cho lỗi thời hạn của chuỗi chứng chỉ."""
    code = getattr(error, "verify_code", None)
    if code in (9, 10, 0x800B0101, -2146762495):
        message = (
            f"Không thể kết nối an toàn tới {host}: chứng chỉ HTTPS đã hết hạn "
            "hoặc chưa có hiệu lực. Kiểm tra ngày giờ máy; nếu đúng, hãy chờ dịch vụ "
            "cập nhật chứng chỉ rồi thử lại."
        )
    else:
        message = (
            f"Không thể kết nối an toàn tới {host}: chứng chỉ HTTPS không hợp lệ. "
            "Hãy thử lại sau hoặc liên hệ hỗ trợ."
        )
    logger.warning(
        "Chứng chỉ HTTPS bị từ chối tại %s [mã=%s]: %s",
        host,
        code,
        getattr(error, "verify_message", str(error)),
    )
    return NetworkError(message)
