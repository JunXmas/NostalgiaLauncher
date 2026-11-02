"""Đồng bộ qua phòng: lõi không bắt buộc gói P2P; trạng thái phòng hỏng ra lỗi rõ ràng."""

import asyncio
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.room_transfer import RoomTransfer


def test_core_imports_without_the_p2p_packages() -> None:
    """`cryptography`/`aiortc` thuộc extra `ui`; `nostalgia.api` phải import được khi thiếu."""
    code = (
        "import sys\n"
        "for name in ('cryptography', 'aiortc', 'aioice'):\n"
        "    sys.modules[name] = None\n"
        "import nostalgia.api\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


class Http:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.reply = SimpleNamespace(body=body, status=status, is_ok=200 <= status < 300)

    def send(self, *_args: Any, **_kwargs: Any) -> Any:
        return self.reply


class Downloader:
    def __init__(self) -> None:
        self.fetched: list[str] = []

    async def fetch_manifest(self, room_code: str, _token: Any) -> str:
        self.fetched.append(room_code)
        return "manifest"


def transfer(body: bytes, status: int = 200) -> tuple[RoomTransfer, Downloader]:
    room = RoomTransfer.__new__(RoomTransfer)
    downloader = Downloader()
    room._direct_allowed, room._joiner, room._room_http = True, object(), Http(body, status)
    room._relay_url, room._guest_room_code = "wss://signal.test", "ABCDEFGHJKMNPQRSTU"
    room._peer_download = downloader  # type: ignore[assignment]
    return room, downloader


@pytest.mark.parametrize(
    "body",
    [b'{"sync_ready": false}', b'{"sync_ready": true, "locked": true}', b'{"sharing": true}'],
)
def test_no_manifest_until_the_host_is_ready_and_unlocked(body: bytes) -> None:
    room, downloader = transfer(body)
    assert asyncio.run(room._fetch_sync_manifest("ABCDEFGHJKMNPQRSTU")) is None
    assert not downloader.fetched


@pytest.mark.parametrize(("body", "status"), [(b"not json", 200), (b"[1, 2]", 200), (b"{}", 503)])
def test_broken_lobby_reply_is_a_clear_room_error(body: bytes, status: int) -> None:
    room, _ = transfer(body, status)
    with pytest.raises(MultiplayerError):
        asyncio.run(room._fetch_sync_manifest("ABCDEFGHJKMNPQRSTU"))


def test_ready_lobby_fetches_the_manifest_from_the_host() -> None:
    room, downloader = transfer(b'{"sync_ready": true, "locked": false}')
    assert asyncio.run(room._fetch_sync_manifest("ABCDEFGHJKMNPQRSTU")) == "manifest"
    assert downloader.fetched == ["ABCDEFGHJKMNPQRSTU"]


def test_missing_peer_file_is_an_error_not_a_silent_skip() -> None:
    room, _ = transfer(b"{}")
    room._direct_allowed = False
    with pytest.raises(MultiplayerError, match="P2P"):
        asyncio.run(room.download_peer_file("ABCDEFGHJKMNPQRSTU", object(), object()))  # type: ignore[arg-type]
