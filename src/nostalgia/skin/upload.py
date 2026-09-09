"""Upload skin lên Mojang API (tài khoản Microsoft premium).

Endpoint: PUT https://api.minecraftservices.com/minecraft/profile/skins
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
Body: variant=classic|slim, file=<skin.png>

Ely.by: chỉ đổi skin qua giao diện web ely.by — API cần session riêng, không hỗ trợ ở đây.
Offline: không có skin server nào, dùng Steve/Alex mặc định.
"""

from __future__ import annotations

import logging
from pathlib import Path

from nostalgia.errors import AccountError, NetworkError
from nostalgia.net.http import HttpClient

logger = logging.getLogger(__name__)

SKIN_UPLOAD_URL = "https://api.minecraftservices.com/minecraft/profile/skins"
MAX_SKIN_SIZE = 256 * 1024  # skin PNG tối đa: 256 KiB (thực tế chỉ ~4 KB)


def upload_skin_to_mojang(
    http_client: HttpClient,
    access_token: str,
    skin_path: Path,
    *,
    slim: bool = False,
) -> None:
    """Gửi file skin PNG lên Mojang. Ném `AccountError` nếu thất bại.

    File phải là PNG 64x64 (hoặc 64x32 cho skin cũ). Mojang trả 204 No Content nếu thành công,
    hoặc mã lỗi JSON nếu sai định dạng/token hết hạn.
    """
    if not skin_path.is_file():
        raise AccountError(f"không tìm thấy file skin: {skin_path}")
    skin_bytes = skin_path.read_bytes()
    if len(skin_bytes) > MAX_SKIN_SIZE:
        raise AccountError(f"file skin quá lớn: {len(skin_bytes)} bytes (tối đa {MAX_SKIN_SIZE})")

    variant = "slim" if slim else "classic"
    boundary = "----NostalgiaSkinUpload"
    body = _build_multipart(boundary, variant, skin_path.name, skin_bytes)

    try:
        response = http_client.send(
            "PUT",
            SKIN_UPLOAD_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            body=body,
        )
    except NetworkError as exc:
        raise AccountError(f"không thể upload skin: {exc}") from exc
    if not response.is_ok:
        detail = response.body[:200].decode(errors="replace")
        raise AccountError(f"Mojang từ chối skin (HTTP {response.status}): {detail}")
    logger.info("đã upload skin %s (%s) lên Mojang", skin_path.name, variant)


def _build_multipart(boundary: str, variant: str, filename: str, content: bytes) -> bytes:
    """Dựng body multipart/form-data thủ công — không kéo thêm thư viện."""
    parts: list[bytes] = []
    # Part 1: variant
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="variant"\r\n\r\n')
    parts.append(f"{variant}\r\n".encode())
    # Part 2: file
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts)
