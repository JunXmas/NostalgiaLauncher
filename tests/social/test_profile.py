"""PNG nhỏ và URL ảnh bị giới hạn; dữ liệu skin không biến thành đường dẫn mạng tùy ý."""

import base64
import struct

import pytest

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue
from nostalgia.social.profile_image import image_url, png
from nostalgia.social.profile_parse import parse_profile


def test_google_avatar_rejects_local_files_credentials_and_lookalike_hosts() -> None:
    assert image_url("https://lh3.googleusercontent.com/a/fixture=s96-c")
    for url in (
        "file:///etc/passwd",
        "http://lh3.googleusercontent.com/a",
        "https://lh3.googleusercontent.com.evil.invalid/a",
        "https://lh3.googleusercontent.com:443/a",
        "https://u@lh3.googleusercontent.com/a",
    ):
        with pytest.raises(SocialError):
            image_url(url)


def test_profile_images_and_pack_lists_are_bounded() -> None:
    payload = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 4096, 4096) + b"x" * 20
    with pytest.raises(SocialError):
        png(base64.b64encode(payload).decode())
    with pytest.raises(SocialError):
        png("a" * 50_000)
    document: dict[str, JsonValue] = {
        "account_id": "misa",
        "name": "Misa",
        "favorite_packs": [{"title": "Pack", "game_version": "1.21.1"}] * 4,
    }
    with pytest.raises(SocialError):
        parse_profile(document)
    with pytest.raises(SocialError):
        parse_profile(document | {"favorite_packs": [], "badge": "Admin"})
