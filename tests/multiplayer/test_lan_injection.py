"""Phát hiện và chống injection port LAN qua MOTD giả mạo."""

from __future__ import annotations

from nostalgia.multiplayer.lan import build_beacon, parse_lan_beacon


def test_injected_ad_tag_in_world_name_uses_real_port() -> None:
    """Tên thế giới chứa [AD]22[/AD] giả không được ghi đè cổng thật ở cuối beacon.

    Kịch bản tấn công: host đặt tên thế giới là "[AD]22[/AD] Trap World", beacon thành
    [MOTD][AD]22[/AD] Trap World[/MOTD][AD]25565[/AD]. Nếu parser lấy thẻ [AD] ĐẦU TIÊN,
    launcher sẽ nối cổng 22 (SSH) thay vì 25565.
    """
    crafted = b"[MOTD][AD]22[/AD] Trap World[/MOTD][AD]25565[/AD]"
    result = parse_lan_beacon(crafted, "127.0.0.1")
    assert result is not None, "beacon hợp lệ phải được nhận diện"
    assert result.world_port == 25565, f"phải lấy cổng thật 25565, nhận được {result.world_port}"
    # Tên thế giới không được chứa thẻ [AD] giả
    assert "[AD]" not in result.world_name
    assert "[/AD]" not in result.world_name


def test_multiple_injected_ad_tags_take_last() -> None:
    """Nhiều thẻ [AD] giả trong MOTD: luôn lấy thẻ CUỐI CÙNG."""
    crafted = b"[MOTD][AD]22[/AD][AD]80[/AD]Evil[/MOTD][AD]8080[/AD]"
    result = parse_lan_beacon(crafted, "127.0.0.1")
    assert result is not None
    assert result.world_port == 8080


def test_injected_privileged_port_via_last_tag_is_rejected() -> None:
    """Ngay cả thẻ cuối cùng mà trỏ vào cổng đặc quyền thì cũng phải từ chối."""
    crafted = b"[MOTD]World[/MOTD][AD]22[/AD]"
    result = parse_lan_beacon(crafted, "127.0.0.1")
    assert result is None, "cổng 22 nằm dưới 1024, phải từ chối"


def test_normal_beacon_still_works() -> None:
    """Beacon bình thường không bị ảnh hưởng bởi bản vá."""
    beacon = build_beacon(25565, "Thế giới bình thường")
    result = parse_lan_beacon(beacon, "127.0.0.1")
    assert result is not None
    assert result.world_port == 25565
    assert result.world_name == "Thế giới bình thường"


def test_world_name_sanitised_of_ad_tags() -> None:
    """Tên thế giới hiển thị phải sạch mọi thẻ [AD]...[/AD]."""
    crafted = b"[MOTD][AD]22[/AD]Hello[/MOTD][AD]25565[/AD]"
    result = parse_lan_beacon(crafted, "127.0.0.1")
    assert result is not None
    assert result.world_port == 25565
    assert "22" in result.world_name or "Hello" in result.world_name
    assert "[AD]" not in result.world_name
