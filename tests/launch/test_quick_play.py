"""Quick play: đời có khối `is_quick_play_singleplayer` (1.20+) nhận `--quickPlaySingleplayer
<thư mục>`; đời không có thì lệnh y hệt bình thường, không ném; không bao giờ để lọt
`--quickPlayPath` (cờ has_quick_plays_support không được bật). Server: 1.20+ nhận
`--quickPlayMultiplayer`, 1.6-1.19 nhận `--server/--port`; địa chỉ sai dạng bị từ chối."""

from __future__ import annotations

import json

import pytest
from test_command import GAME_DIR, VERSION_IDS, build, meta_for

from nostalgia.launch.command import LaunchOptions, describe_quick_play, split_server_address
from version_fixtures import load_fixture


def _has_quick_play_block(version_id: str, marker: str = "quickPlaySingleplayer") -> bool:
    """Fixture (kể cả bản cha mà loader kế thừa) có khai `--quickPlaySingleplayer` không."""
    raw = load_fixture(version_id)
    parent_id = raw.get("inheritsFrom")
    text = json.dumps(raw)
    if isinstance(parent_id, str):
        text += json.dumps(load_fixture(parent_id))
    return marker in text


@pytest.mark.parametrize("version_id", VERSION_IDS)
def test_world_folder_reaches_only_versions_that_understand_it(version_id: str) -> None:
    argv = build(version_id, options=LaunchOptions(game_dir=GAME_DIR, world_folder="Nhà")).argv
    plain = build(version_id).argv
    if _has_quick_play_block(version_id):
        position = argv.index("--quickPlaySingleplayer")
        assert argv[position + 1] == "Nhà"
        assert [
            argument
            for argument in argv
            if argument != "--quickPlaySingleplayer" and argument != "Nhà"
        ] == list(plain)
    else:
        assert argv == plain, "đời cũ: vào thẳng thế giới là điều game không biết — mở bình thường"
    assert "--quickPlayPath" not in argv
    assert not any("${" in argument for argument in argv)


def test_the_new_fixtures_do_carry_the_block() -> None:
    assert _has_quick_play_block("1.20.1") and _has_quick_play_block("1.21.4")
    assert not _has_quick_play_block("1.12.2")


@pytest.mark.parametrize("version_id", VERSION_IDS)
def test_server_address_reaches_every_version_that_understands_one(version_id: str) -> None:
    address = "play.example:25566"
    argv = build(version_id, options=LaunchOptions(game_dir=GAME_DIR, server_address=address)).argv
    plain = build(version_id).argv
    if _has_quick_play_block(version_id, "quickPlayMultiplayer"):
        position = argv.index("--quickPlayMultiplayer")
        assert argv[position + 1] == address
        added = ["--quickPlayMultiplayer", address]
    else:
        # 1.8.9 / 1.12.2: chưa có quick play nhưng đã hiểu --server/--port từ 1.6.
        assert argv[-4:] == ("--server", "play.example", "--port", "25566")
        added = ["--server", "play.example", "--port", "25566"]
    assert [argument for argument in argv if argument not in added] == list(plain)
    assert "--quickPlaySingleplayer" not in argv and "--quickPlayPath" not in argv
    assert not any("${" in argument for argument in argv)


def test_old_versions_get_the_default_port_and_bare_ipv6() -> None:
    options = LaunchOptions(game_dir=GAME_DIR, server_address="[2001:db8::1]")
    assert build("1.12.2", options=options).argv[-4:] == (
        "--server",
        "2001:db8::1",
        "--port",
        "25565",
    )


def test_server_addresses_must_look_like_host_and_port() -> None:
    assert split_server_address("mc.hypixel.net") == ("mc.hypixel.net", "25565")
    assert split_server_address("192.168.1.5:25566") == ("192.168.1.5", "25566")
    assert split_server_address("[::1]:7") == ("::1", "7")
    for bad in ("", "--demo", "-x.example", "a b", "a.example:0", "a.example:65536", "::1", "a:b"):
        assert split_server_address(bad) is None, bad
        with pytest.raises(ValueError, match="không hợp lệ"):
            LaunchOptions(game_dir=GAME_DIR, server_address=bad) if bad else _refuse_empty()


def _refuse_empty() -> None:
    raise ValueError("không hợp lệ")  # rỗng nghĩa là "không vào server", không phải lỗi


def test_support_is_read_from_the_version_rules() -> None:
    assert describe_quick_play(meta_for("1.21.4")) == describe_quick_play(meta_for("1.20.1"))
    new = describe_quick_play(meta_for("fabric-loader-0.19.3-1.21.4"))
    assert (new.worlds, new.servers) == (True, True)
    old = describe_quick_play(meta_for("1.12.2"))
    assert (old.worlds, old.servers) == (False, True)


def test_world_and_server_together_are_refused() -> None:
    with pytest.raises(ValueError, match="MỘT nơi"):
        LaunchOptions(game_dir=GAME_DIR, world_folder="Nhà", server_address="play.example")
