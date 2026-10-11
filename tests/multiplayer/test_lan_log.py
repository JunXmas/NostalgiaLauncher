"""Log mới, bị cắt hoặc xoay vòng đều nhận đúng LAN; không dùng cổng của lần chơi trước."""

from pathlib import Path

from nostalgia.multiplayer.lan_log import READ_LIMIT, LanLogReader


def test_old_announcement_is_ignored_and_new_append_is_read(tmp_path: Path) -> None:
    path = tmp_path / "latest.log"
    path.write_text("Started serving on 51234\n")
    reader = LanLogReader(path)
    assert reader.read_port() == 0
    with path.open("a") as stream:
        stream.write("[Server thread/INFO]: Started serving on 54321\n")
    assert reader.read_port() == 54321
    assert reader.read_port() == 0


def test_missing_log_can_appear_with_a_partial_announcement(tmp_path: Path) -> None:
    path = tmp_path / "latest.log"
    reader = LanLogReader(path)
    assert reader.read_port() == 0
    path.write_text("[Server thread/INFO]: Started serving on 54")
    assert reader.read_port() == 0
    with path.open("a") as stream:
        stream.write("321\n")
    assert reader.read_port() == 54321


def test_truncated_log_and_replaced_log_start_from_zero(tmp_path: Path) -> None:
    path = tmp_path / "latest.log"
    path.write_text("old log\n" * 100)
    reader = LanLogReader(path)
    path.write_text("Started serving on 54321\n")
    assert reader.read_port() == 54321
    path.rename(tmp_path / "previous.log")
    path.write_text("Started serving on 51234\n")
    assert reader.read_port() == 51234


def test_log_flood_is_bounded_and_chat_cannot_supply_a_port(tmp_path: Path) -> None:
    path = tmp_path / "latest.log"
    reader = LanLogReader(path)
    path.write_bytes(
        b"x" * (READ_LIMIT * 3)
        + b"\n[Server thread/INFO]: Started serving on 54321\n"
        + b"[Render thread/INFO]: [CHAT] <guest> Local game hosted on port 51234\n"
    )
    assert reader.read_port() == 54321
    assert reader.read_port() == 0
