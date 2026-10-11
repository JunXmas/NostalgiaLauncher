"""Thời lượng P2P luôn hữu hạn; nối lại không bỏ xác thực hay chống phát lại."""

import asyncio
import json
import time
from typing import cast

import pytest
from test_peer_transport import Signalling, local_ice

from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_failure import PeerConnectionError
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.net.http import HttpClient, HttpResponse


@pytest.mark.parametrize("duration", [0, -1, 46, 999999, True, None, "45"])
def test_host_refuses_unbounded_or_malformed_peer_lifetime(duration: object) -> None:
    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 25565)
        peer = PeerHost(host)
        await peer._answer(
            json.dumps(
                {
                    "id": "a" * 32,
                    "purpose": "game",
                    "body": "bad",
                    "expires_at": 123456,
                    "ttl_seconds": duration,
                }
            ).encode(),
            time.monotonic(),
        )
        assert not peer.connections and not peer._seen
        await peer.close()

    asyncio.run(scenario())


def test_failed_ice_reports_network_stage_without_waiting_for_channel_timeout(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    local_ice(monkeypatch)

    async def blocked(_connection: object) -> None:
        raise ConnectionError("test network blocks UDP")

    monkeypatch.setattr("aioice.Connection.connect", blocked)

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 25565)
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        started_at = time.monotonic()
        try:
            with pytest.raises(PeerConnectionError, match="UDP") as caught:
                await connect_peer(
                    "https://signal.test", "ABCDEFABCDEFGHJKMN", "game", cast(HttpClient, Http())
                )
            assert caught.value.retryable and time.monotonic() - started_at < 3
            assert signal.purposes == ["game"]
            notes = " ".join(
                record.message
                for record in caplog.records
                if record.name == "nostalgia.multiplayer.peer_connection"
            )
            assert "channel" in notes
            assert all(
                secret not in notes for secret in ("ABCDEFGHJKMN", "127.0.0.1", "a=fingerprint")
            )
        finally:
            await host.close()

    asyncio.run(scenario())


def test_queued_expired_request_cannot_gain_a_new_lifetime() -> None:
    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 25565)
        peer = PeerHost(host)
        await peer._answer(
            json.dumps(
                {
                    "id": "a" * 32,
                    "purpose": "game",
                    "body": "bad",
                    "expires_at": 123456,
                    "ttl_seconds": 45,
                }
            ).encode(),
            time.monotonic() - 46,
        )
        assert not peer.connections and not peer._seen
        await peer.close()

    asyncio.run(scenario())


def test_replayed_offer_does_not_create_another_connection_or_extend_lease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_ice(monkeypatch)

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 25565)
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal
        offers: list[bytes] = []

        class Http:
            def send(self, method: str, url: str, **kwargs: object) -> HttpResponse:
                offers.append(cast(bytes, kwargs["body"]))
                return signal.send_http(method, url, **kwargs)

        stream = await connect_peer(
            "https://signal.test", "ABCDEFABCDEFGHJKMN", "game", cast(HttpClient, Http())
        )
        try:
            document = json.loads(offers[0])
            document.update(expires_at=int(time.time()) + 45, ttl_seconds=45)
            seen = dict(host.peer._seen)
            await host.peer._answer(json.dumps(document).encode(), time.monotonic())
            assert host.peer._seen == seen and len(host.peer.connections) == 1
        finally:
            await stream.close()
            await host.close()

    asyncio.run(scenario())
