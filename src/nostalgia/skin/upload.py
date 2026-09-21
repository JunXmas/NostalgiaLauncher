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
import struct
from pathlib import Path

from nostalgia.errors import AccountError, NetworkError
from nostalgia.net.http import HttpClient
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints

logger = logging.getLogger(__name__)

MAX_SKIN_SIZE = 256 * 1024  # skin PNG tối đa: 256 KiB (thực tế chỉ ~4 KB)
VALID_SKIN_SIZES = ((64, 64), (64, 32))  # Mojang chỉ chấp nhận đúng hai kích thước này
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _read_png_dimensions(content: bytes) -> tuple[int, int]:
    """Đọc width/height từ chunk IHDR (8 byte signature + 4 byte length + "IHDR" + 8 byte kích
    thước). Không dùng thư viện ảnh ngoài — IHDR luôn nằm cố định ở đầu file PNG hợp lệ."""
    if not content.startswith(_PNG_SIGNATURE) or len(content) < 24:
        raise AccountError("file skin không phải PNG hợp lệ")
    if content[12:16] != b"IHDR":
        raise AccountError("file skin không phải PNG hợp lệ (thiếu chunk IHDR)")
    width, height = struct.unpack(">II", content[16:24])
    return width, height


def upload_skin_to_mojang(
    http_client: HttpClient,
    access_token: str,
    skin_path: Path,
    *,
    slim: bool = False,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
) -> None:
    """Gửi file skin PNG lên Mojang. Ném `AccountError` nếu thất bại.

    File phải là PNG 64x64 (hoặc 64x32 cho skin cũ) — kiểm ngay tại đây, vì Mojang từ chối
    muộn với thông báo khó hiểu. Mojang trả 204 No Content nếu thành công, hoặc mã lỗi kèm
    thân phản hồi nếu sai định dạng/token hết hạn.
    """
    if not skin_path.is_file():
        raise AccountError(f"không tìm thấy file skin: {skin_path}")
    skin_bytes = skin_path.read_bytes()
    if len(skin_bytes) > MAX_SKIN_SIZE:
        raise AccountError(f"file skin quá lớn: {len(skin_bytes)} bytes (tối đa {MAX_SKIN_SIZE})")
    dimensions = _read_png_dimensions(skin_bytes)
    if dimensions not in VALID_SKIN_SIZES:
        width, height = dimensions
        raise AccountError(f"skin phải là PNG 64x64 (hoặc 64x32) — ảnh này {width}x{height}")

    variant = "slim" if slim else "classic"
    boundary = "----NostalgiaSkinUpload"
    body = _build_multipart(boundary, variant, skin_path.name, skin_bytes)

    try:
        response = http_client.send(
            "PUT",
            endpoints.skin_upload,
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
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="variant"\r\n\r\n')
    parts.append(f"{variant}\r\n".encode())
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts)
