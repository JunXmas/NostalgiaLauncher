"""Quick play: đời có khối `is_quick_play_singleplayer` (1.20+) nhận `--quickPlaySingleplayer
<thư mục>`; đời không có thì lệnh y hệt bình thường, không ném; không bao giờ để lọt
`--quickPlayPath` (cờ has_quick_plays_support không được bật)."""

from __future__ import annotations

import json

import pytest
from test_command import GAME_DIR, VERSION_IDS, build

from nostalgia.launch.command import LaunchOptions
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
def test_server_address_reaches_only_versions_that_understand_it(version_id: str) -> None:
    address = "play.example:25565"
    argv = build(version_id, options=LaunchOptions(game_dir=GAME_DIR, server_address=address)).argv
    plain = build(version_id).argv
    if _has_quick_play_block(version_id, "quickPlayMultiplayer"):
        position = argv.index("--quickPlayMultiplayer")
        assert argv[position + 1] == address
        assert [
            argument
            for argument in argv
            if argument != "--quickPlayMultiplayer" and argument != address
        ] == list(plain)
    else:
        assert argv == plain, "đời cũ: mở game bình thường, không lỗi"
    assert "--quickPlaySingleplayer" not in argv and "--quickPlayPath" not in argv
    assert not any("${" in argument for argument in argv)


def test_world_and_server_together_are_refused() -> None:
    with pytest.raises(ValueError, match="MỘT nơi"):
        LaunchOptions(game_dir=GAME_DIR, world_folder="Nhà", server_address="play.example")
