"""ICE/STUN chọn đường trực tiếp; DTLS/SCTP mã hoá dữ liệu bằng aiortc."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidTag

from nostalgia.errors import MultiplayerError, NetworkError
from nostalgia.multiplayer.peer_codec import (
    PeerDescription,
    build_peer_envelope,
    parse_peer_envelope,
)
from nostalgia.multiplayer.peer_failure import (
    PeerConnectionError,
    connection_failure,
    negotiation_refusal,
)
from nostalgia.multiplayer.peer_stream import PeerStream
from nostalgia.multiplayer.peer_stun import select_peer_configuration
from nostalgia.multiplayer.room_code import split_room_code
from nostalgia.multiplayer.sync_gateway import invite_proof
from nostalgia.net.http import HttpClient

if TYPE_CHECKING:
    from aiortc import RTCConfiguration, RTCPeerConnection


def build_peer_configuration(*, stun: bool = True) -> RTCConfiguration:
    from aiortc import RTCConfiguration, RTCIceServer

    return RTCConfiguration(
        iceServers=[RTCIceServer(urls="stun:stun.cloudflare.com:3478")] if stun else []
    )


async def connect_peer(
    base_url: str, room_code: str, purpose: str, http_client: HttpClient
) -> PeerStream:
    from aiortc import RTCPeerConnection, RTCSessionDescription

    room_id, room_secret = split_room_code(room_code)
    _, proof = invite_proof(room_code)
    request_id = secrets.token_hex(16)
    configuration = await select_peer_configuration(build_peer_configuration())
    connection = RTCPeerConnection(configuration)
    stream = PeerStream(connection, connection.createDataChannel("nostalgia-" + purpose))
    stage, started_at = "gathering", time.monotonic()
    try:
        async with asyncio.timeout(15):
            await connection.setLocalDescription(await connection.createOffer())
        description = connection.localDescription
        assert description is not None
        envelope = build_peer_envelope(
            room_secret, request_id, purpose, PeerDescription(description.sdp, description.type)
        )
        stage = "signalling"
        async with asyncio.timeout(25):
            response = await asyncio.to_thread(
                http_client.send,
                "POST",
                base_url.rstrip("/") + f"/v1/rooms/{room_id}/peer",
                headers={"X-Room-Invite-Proof": proof, "Content-Type": "application/json"},
                body=json.dumps({"id": request_id, "purpose": purpose, "body": envelope}).encode(),
                max_bytes=96000,
            )
            if not response.is_ok:
                logging.getLogger(__name__).warning(
                    "P2P %s signalling refused: HTTP %s", purpose, response.status
                )
                raise negotiation_refusal(response.status, purpose)
            document = json.loads(response.body)
            if document["id"] != request_id:
                raise ValueError("peer answer scope mismatch")
            answer = parse_peer_envelope(room_secret, request_id, purpose, document["body"])
            if answer.description_kind != "answer":
                raise ValueError("invalid peer answer")
        stage = "channel"
        async with asyncio.timeout(35):
            await connection.setRemoteDescription(RTCSessionDescription(answer.sdp, "answer"))
            await stream.wait_open(timeout=30)
            logging.getLogger(__name__).info(
                "P2P %s connected in %.1fs", purpose, time.monotonic() - started_at
            )
            return stream
    except PeerConnectionError:
        await stream.close()
        raise
    except (InvalidTag, ValueError, KeyError, TypeError) as exc:
        await stream.close()
        raise MultiplayerError(
            "Không xác thực được kết nối trực tiếp; hãy nhận lại lời mời."
        ) from exc
    except (ConnectionError, TimeoutError, NetworkError) as exc:
        logging.getLogger(__name__).warning(
            "P2P %s failed at %s after %.1fs: %s",
            purpose,
            stage,
            time.monotonic() - started_at,
            type(exc).__name__,
        )
        await stream.close()
        raise connection_failure(stage) from exc
    except Exception as exc:
        await stream.close()
        raise MultiplayerError(
            "Không thể hoàn tất kết nối trực tiếp; hãy nhận lại lời mời."
        ) from exc
    except BaseException:
        await stream.close()
        raise


async def answer_peer(
    connection: RTCPeerConnection, room_secret: str, request_id: str, purpose: str, encoded: str
) -> str:
    from aiortc import RTCSessionDescription

    description = parse_peer_envelope(room_secret, request_id, purpose, encoded)
    if description.description_kind != "offer":
        raise ValueError("invalid peer offer")
    await connection.setRemoteDescription(RTCSessionDescription(description.sdp, "offer"))
    await connection.setLocalDescription(await connection.createAnswer())
    answer = connection.localDescription
    assert answer is not None
    return build_peer_envelope(
        room_secret, request_id, purpose, PeerDescription(answer.sdp, answer.type)
    )
