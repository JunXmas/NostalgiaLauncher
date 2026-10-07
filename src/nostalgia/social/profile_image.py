"""URL Google và PNG giới hạn kích thước cho hồ sơ."""

import base64
import re
import struct
from urllib.parse import urlsplit

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue, as_string


def image_url(document: JsonValue) -> str:
    value = as_string(document) or ""
    if not value:
        return ""
    prefix = "data:image/png;base64,"
    if value.startswith(prefix):
        png(value[len(prefix) :], 8, 512)
        return value
    try:
        parts = urlsplit(value)
    except ValueError as exc:
        raise SocialError("Ảnh đại diện không hợp lệ.") from exc
    if (
        len(value) > 1024
        or parts.scheme != "https"
        or not re.fullmatch(r"lh[0-9]+\.googleusercontent\.com", parts.netloc)
        or parts.fragment
        or not parts.path.startswith("/")
    ):
        raise SocialError("Ảnh đại diện không hợp lệ.")
    return value


def png(document: JsonValue, dimension: int = 64, maximum: int = 32768) -> str:
    value = as_string(document) or ""
    if not value:
        return ""
    try:
        if len(value) > (maximum + 2) // 3 * 4:
            raise ValueError("oversized")
        payload = base64.b64decode(value, validate=True)
        if (
            not 33 <= len(payload) <= maximum
            or payload[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            or struct.unpack(">II", payload[16:24]) != (dimension, dimension)
        ):
            raise ValueError("invalid PNG dimensions")
    except ValueError as exc:
        raise SocialError("Skin hồ sơ không hợp lệ.") from exc
    return value
