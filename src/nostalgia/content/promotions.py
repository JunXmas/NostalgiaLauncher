"""Slide quảng cáo trang chủ: `promotions.json` trong kho GitHub, đổi nội dung không cần ra bản.

Tương thích tiến: chỉ tăng `schema` khi đổi KHÔNG tương thích (launcher cũ gặp schema mới
hơn thì bỏ cả feed, dùng bản đệm). Thêm field hay loại slide mới thì giữ schema: field lạ
bị bỏ qua, slide có `kind` lạ bị bỏ qua riêng nó, nên launcher cũ vẫn hiện phần nó hiểu.

An toàn: feed và ảnh chỉ tải từ host ghim, không theo chuyển hướng (`HttpClient.send`), có
trần dung lượng, ảnh phải là PNG/JPEG thật và không quá lớn; link chỉ `https`; server đúng
dạng `host:port`. Feed tốt cuối cùng cùng ảnh được giữ trong đệm để dùng khi offline.
"""

from __future__ import annotations

import hashlib
import logging
import re
import struct
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from nostalgia.errors import DataFileError, NetworkError, NostalgiaError
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.storage.atomic_bytes import atomic_write
from nostalgia.storage.files import ensure_dir

logger = logging.getLogger(__name__)

SCHEMA = 1
MAX_FEED_BYTES = 64 * 1024
MAX_IMAGE_BYTES = 1024 * 1024
MAX_IMAGE_SIDE = 2560
MAX_SLIDES = 8
LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?"
SERVER_ADDRESS = re.compile(rf"(?=.{{1,253}}:){LABEL}(?:\.{LABEL})*:(\d{{1,5}})")


@dataclass(frozen=True, slots=True)
class Promotion:
    slide_type: Literal["server", "link"]
    title: str
    body: str
    button: str
    # `host:port` với slide server, URL https với slide link.
    target: str
    image: Path | None
    starts_at: int
    ends_at: int

    def showing(self, now: float) -> bool:
        return self.starts_at <= now and (not self.ends_at or now < self.ends_at)


# (url ảnh, đường dẫn trong đệm) -> ảnh đã sẵn sàng ở đường dẫn đó chưa.
type ImageReady = Callable[[str, Path], bool]


def load_promotions(
    cache_dir: Path, http_client: HttpClient, feed_url: str, hosts: tuple[str, ...]
) -> tuple[Promotion, ...]:
    """Feed mới nhất; hỏng hay offline thì bản đệm; không có đệm thì rỗng (ẩn slide). CHẠM MẠNG."""
    try:
        return _refresh(cache_dir, http_client, feed_url, hosts)
    except NostalgiaError as error:
        logger.warning("Không tải được quảng cáo trang chủ, dùng bản đệm: %s", error)
    try:
        payload = (cache_dir / "feed.json").read_bytes()
        return _parse(payload, cache_dir, hosts, lambda _url, path: path.is_file())
    except (OSError, NostalgiaError) as error:
        logger.warning("Không có bản đệm quảng cáo, ẩn slide quảng cáo: %s", error)
        return ()


def _refresh(
    cache_dir: Path, http_client: HttpClient, feed_url: str, hosts: tuple[str, ...]
) -> tuple[Promotion, ...]:
    payload = _fetch(http_client, _pinned(feed_url, hosts), MAX_FEED_BYTES)
    ensure_dir(cache_dir / "images")

    def fetch_image(url: str, path: Path) -> bool:
        if path.is_file():
            return True
        try:
            image = _fetch(http_client, url, MAX_IMAGE_BYTES)
            _check_image(image)
        except NostalgiaError as error:
            logger.debug("Bỏ slide vì ảnh %s hỏng: %s", url, error)
            return False
        atomic_write(path, image)
        return True

    promotions = _parse(payload, cache_dir, hosts, fetch_image)
    atomic_write(cache_dir / "feed.json", payload)
    kept = {promotion.image for promotion in promotions}
    for stale in (cache_dir / "images").iterdir():
        if stale not in kept:
            stale.unlink(missing_ok=True)
    return promotions


def _fetch(http_client: HttpClient, url: str, limit: int) -> bytes:
    response = http_client.send("GET", url, max_bytes=limit)
    if response.status != 200:
        raise NetworkError(f"{url} trả về mã {response.status}")
    return response.body


def _pinned(url: str, hosts: tuple[str, ...]) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in hosts or parts.username:
        raise DataFileError(f"địa chỉ không nằm trên host cho phép: {url!r}")
    return url


def _parse(
    payload: bytes, cache_dir: Path, hosts: tuple[str, ...], image_ready: ImageReady
) -> tuple[Promotion, ...]:
    document = as_mapping(decode_json(payload, what="feed quảng cáo"))
    schema = as_integer(document.get("schema"))
    if schema != SCHEMA:
        raise DataFileError(f"feed quảng cáo schema {schema!r}, launcher hiểu schema {SCHEMA}")
    promotions: list[Promotion] = []
    for raw in as_list(document.get("slides"))[:MAX_SLIDES]:
        try:
            promotion = _slide(as_mapping(raw), cache_dir, hosts, image_ready)
        except DataFileError as error:
            logger.debug("Bỏ một slide quảng cáo: %s", error)
            continue
        if promotion is not None:
            promotions.append(promotion)
    return tuple(promotions)


def _slide(
    fields: dict[str, JsonValue], cache_dir: Path, hosts: tuple[str, ...], image_ready: ImageReady
) -> Promotion | None:
    slide_type: Literal["server", "link"]
    if fields.get("kind") == "server":
        slide_type = "server"
        target = _text(fields, "address", 260)
        port = SERVER_ADDRESS.fullmatch(target)
        if port is None or not 1 <= int(port[1]) <= 65535:
            raise DataFileError(f"địa chỉ server phải là host:port: {target!r}")
    elif fields.get("kind") == "link":
        slide_type = "link"
        target = _text(fields, "url", 512)
        parts = urlsplit(target)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise DataFileError(f"link phải là https: {target!r}")
    else:
        return None
    image = None
    if image_url := as_string(fields.get("image")):
        _pinned(image_url, hosts)
        suffix = ".png" if image_url.lower().endswith(".png") else ".jpg"
        name = hashlib.sha256(image_url.encode()).hexdigest()[:32] + suffix
        image = cache_dir / "images" / name
        if not image_ready(image_url, image):
            raise DataFileError(f"ảnh không dùng được: {image_url!r}")
    starts_at, ends_at = (as_integer(fields.get(key, 0)) for key in ("starts_at", "ends_at"))
    if starts_at is None or ends_at is None or starts_at < 0 or ends_at < 0:
        raise DataFileError("starts_at/ends_at phải là giây Unix")
    return Promotion(
        slide_type,
        _text(fields, "title", 60),
        _text(fields, "body", 220, required=False),
        _text(fields, "button", 30),
        target,
        image,
        starts_at,
        ends_at,
    )


def _text(fields: dict[str, JsonValue], key: str, limit: int, *, required: bool = True) -> str:
    value = (as_string(fields.get(key)) or "").strip()
    if (required and not value) or len(value) > limit or re.search(r"[\x00-\x1f\x7f]", value):
        raise DataFileError(f"trường {key!r} của slide không hợp lệ")
    return value


def _check_image(image: bytes) -> None:
    """Chỉ nhận PNG/JPEG thật (đúng magic) và không quá MAX_IMAGE_SIDE mỗi chiều."""
    if image.startswith(b"\x89PNG\r\n\x1a\n") and image[12:16] == b"IHDR":
        width, height = struct.unpack(">II", image[16:24])
    elif image.startswith(b"\xff\xd8\xff"):
        width = height = 0
        offset = 2
        while offset + 9 <= len(image) and image[offset] == 0xFF:
            marker, length = image[offset + 1], int.from_bytes(image[offset + 2 : offset + 4])
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", image[offset + 5 : offset + 9])
                break
            offset += 2 + length
    else:
        raise DataFileError("ảnh không phải PNG hay JPEG")
    if not (0 < width <= MAX_IMAGE_SIDE and 0 < height <= MAX_IMAGE_SIDE):
        raise DataFileError(f"ảnh {width}x{height} vượt giới hạn {MAX_IMAGE_SIDE}px")
