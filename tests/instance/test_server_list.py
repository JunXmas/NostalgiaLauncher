"""servers.dat: đọc tên / địa chỉ / icon đúng thứ tự trong game, bỏ server ẩn và server không
địa chỉ, icon hỏng → rỗng nhưng server vẫn còn, file hỏng kiểu gì cũng trả rỗng."""

from __future__ import annotations

import base64
import gzip
from pathlib import Path

from nbt_fixture import build_servers_dat, tiny_png
from nostalgia.instance.server_list import (
    MAX_SERVERS_BYTES,
    SavedServer,
    icon_url_of,
    load_saved_servers,
)

ICON = base64.b64encode(tiny_png()).decode()


def test_reads_servers_in_game_order_and_skips_hidden_or_empty_ones(tmp_path: Path) -> None:
    servers_path = tmp_path / "servers.dat"
    servers_path.write_bytes(
        build_servers_dat(
            [
                ("Hypixel", "mc.hypixel.net", ICON, False),
                ("Bạn bè", "192.168.1.5:25566", None, False),
                ("Ẩn", "hidden.example", ICON, True),
                ("Không địa chỉ", "  ", None, False),
                ("", "chi-dia-chi.example", None, False),
            ]
        )
    )
    assert load_saved_servers(servers_path) == (
        SavedServer("Hypixel", "mc.hypixel.net", ICON),
        SavedServer("Bạn bè", "192.168.1.5:25566", ""),
        SavedServer("chi-dia-chi.example", "chi-dia-chi.example", ""),
    )
    assert icon_url_of(ICON).startswith("data:image/png;base64,") and icon_url_of("") == ""


def test_bad_icons_are_dropped_but_the_server_stays(tmp_path: Path) -> None:
    oversized = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * (40 * 1024)).decode()
    not_png = base64.b64encode(b"khong phai png").decode()
    servers_path = tmp_path / "servers.dat"
    servers_path.write_bytes(
        build_servers_dat(
            [
                ("A", "a.example", "@@@", False),
                ("B", "b.example", not_png, False),
                ("C", "c.example", oversized, False),
            ]
        )
    )
    assert [server.icon_base64 for server in load_saved_servers(servers_path)] == ["", "", ""]
    assert [server.address for server in load_saved_servers(servers_path)] == [
        "a.example",
        "b.example",
        "c.example",
    ]


def test_corrupt_files_return_nothing(tmp_path: Path) -> None:
    healthy = build_servers_dat([("A", "a.example", None, False)])
    cases = {
        "cut.dat": healthy[: len(healthy) // 2],
        "empty.dat": b"",
        "gzipped-by-mistake.dat": gzip.compress(healthy),
        "lying-count.dat": b"\x0a\x00\x00\x09\x00\x07servers\x0a\x00\x0f\x42\x3f",
        "too-big.dat": b"\x0a\x00\x00" + b"\x00" * (MAX_SERVERS_BYTES + 1),
        "no-list.dat": b"\x0a\x00\x00\x00",
    }
    for name, payload in cases.items():
        servers_path = tmp_path / name
        servers_path.write_bytes(payload)
        assert load_saved_servers(servers_path) == (), name
    assert load_saved_servers(tmp_path / "khong-co.dat") == ()
    empty_list = tmp_path / "empty-list.dat"
    empty_list.write_bytes(build_servers_dat([]))
    assert load_saved_servers(empty_list) == ()
