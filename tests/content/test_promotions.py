"""Feed quảng cáo trang chủ: tương thích tiến, host ghim, ảnh/link/server độc, đệm khi offline."""

from __future__ import annotations

import json
import logging
import struct
import time
import zlib
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.content.promotions import Promotion, load_promotions
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import HttpClient

HOSTS = ("localhost",)


def png(width: int = 4, height: int = 2) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = struct.pack(">I", len(header)) + b"IHDR" + header
    return b"\x89PNG\r\n\x1a\n" + chunk + struct.pack(">I", zlib.crc32(b"IHDR" + header))


def jpeg(width: int = 4, height: int = 2) -> bytes:
    frame = b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", height, width) + b"\x03" + b"\x00" * 9
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + frame


def server_slide(**fields: JsonValue) -> dict[str, JsonValue]:
    return {
        "kind": "server",
        "title": "Server cộng đồng",
        "button": "Vào server",
        "address": "play.example.vn:25565",
        **fields,
    }


def link_slide(**fields: JsonValue) -> dict[str, JsonValue]:
    return {
        "kind": "link",
        "title": "Thuê server",
        "button": "Xem",
        "url": "https://x.vn",
        **fields,
    }


def load(
    tmp_path: Path,
    server: LocalHttpsServer,
    state: ServerState,
    http_client: HttpClient,
    feed: object,
) -> tuple[Promotion, ...]:
    state.add("/promotions.json", json.dumps(feed).encode())
    return load_promotions(tmp_path / "cache", http_client, server.url("/promotions.json"), HOSTS)


def test_valid_slides_and_unknown_fields_or_kinds_are_tolerated(
    tmp_path: Path, server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    server_state.add("/a.png", png())
    server_state.add("/b.jpg", jpeg())
    feed = {
        "schema": 1,
        "future_field": {"x": 1},
        "slides": [
            server_slide(image=server.url("/a.png"), colour="red"),
            {"kind": "video", "title": "Loại mới", "button": "Xem", "src": "x"},
            link_slide(image=server.url("/b.jpg"), body="Giá rẻ"),
        ],
    }
    slides = load(tmp_path, server, server_state, http_client, feed)
    assert [(s.slide_type, s.target) for s in slides] == [
        ("server", "play.example.vn:25565"),
        ("link", "https://x.vn"),
    ]
    assert all(s.image is not None and s.image.is_file() for s in slides)


@pytest.mark.parametrize(
    "feed",
    [
        {"schema": 1, "slides": []},
        {"schema": 2, "slides": [server_slide()]},
        {"slides": [server_slide()]},
        {"schema": 1, "slides": [server_slide(address="play.example.vn")]},
        {"schema": 1, "slides": [server_slide(address="a b:25565")]},
        {"schema": 1, "slides": [server_slide(address="x.vn:99999")]},
        {"schema": 1, "slides": [link_slide(url="http://x.vn")]},
        {"schema": 1, "slides": [link_slide(url="javascript:alert(1)")]},
        {"schema": 1, "slides": [link_slide(url="https://user:pw@x.vn")]},
        {"schema": 1, "slides": [link_slide(title="")]},
        {"schema": 1, "slides": [link_slide(title="x" * 200)]},
        {"schema": 1, "slides": [link_slide(ends_at="soon")]},
    ],
)
def test_empty_newer_schema_or_bad_slides_show_nothing(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    feed: object,
) -> None:
    assert load(tmp_path, server, server_state, http_client, feed) == ()


@pytest.mark.parametrize(
    "image",
    [
        b"<svg onload=alert(1)>",
        b"GIF89a" + b"\x00" * 40,
        png(4000, 10),
        jpeg(10, 4000),
        png() + b"\x00" * (1024 * 1024),
    ],
)
def test_bad_images_drop_only_their_slide(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    image: bytes,
) -> None:
    server_state.add("/bad.png", image)
    feed = {"schema": 1, "slides": [server_slide(image=server.url("/bad.png")), link_slide()]}
    slides = load(tmp_path, server, server_state, http_client, feed)
    assert [s.slide_type for s in slides] == ["link"]


def test_feed_and_images_only_from_pinned_hosts(
    tmp_path: Path, server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    server_state.add("/a.png", png())
    foreign = server.url("/a.png").replace("localhost", "127.0.0.1")
    feed = {"schema": 1, "slides": [server_slide(image=foreign), link_slide()]}
    assert [s.slide_type for s in load(tmp_path, server, server_state, http_client, feed)] == [
        "link"
    ]
    assert server_state.request_count("/a.png") == 0
    pinned_elsewhere = load_promotions(
        tmp_path / "other", http_client, server.url("/promotions.json"), ("example.com",)
    )
    assert pinned_elsewhere == ()


def test_starts_at_and_ends_at_expire_slides(
    tmp_path: Path, server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    now = int(time.time())
    feed = {
        "schema": 1,
        "slides": [
            link_slide(title="Đã hết", ends_at=now - 1),
            link_slide(title="Chưa tới", starts_at=now + 3600),
            link_slide(title="Đang chạy", starts_at=now - 10, ends_at=now + 3600),
        ],
    }
    slides = load(tmp_path, server, server_state, http_client, feed)
    assert [s.title for s in slides if s.showing(now)] == ["Đang chạy"]


def test_offline_or_broken_feed_uses_cache_else_hides_with_warning(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    server_state.add("/a.png", png())
    feed = {"schema": 1, "slides": [server_slide(image=server.url("/a.png"))]}
    first = load(tmp_path, server, server_state, http_client, feed)
    server_state.add("/promotions.json", b"{broken", status=200)
    url = server.url("/promotions.json")
    assert load_promotions(tmp_path / "cache", http_client, url, HOSTS) == first
    server_state.add("/promotions.json", b"", status=503)
    assert load_promotions(tmp_path / "cache", http_client, url, HOSTS) == first
    assert any("bản đệm" in record.getMessage() for record in caplog.records)
    caplog.clear()
    assert load_promotions(tmp_path / "empty", http_client, url, HOSTS) == ()
    assert any("ẩn slide" in record.getMessage() for record in caplog.records)


def test_repository_feed_is_valid_and_neutral() -> None:
    feed = json.loads((Path(__file__).parents[2] / "promotions.json").read_text("utf-8"))
    assert feed["schema"] == 1 and isinstance(feed["slides"], list)
    assert "forgotten" not in json.dumps(feed).lower()
