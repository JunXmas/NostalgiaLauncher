"""ICE/STUN chọn đường trực tiếp; DTLS/SCTP mã hoá dữ liệu bằng aiortc."""

from __future__ import annotations

import asyncio
import json
import secrets
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidTag

from nostalgia.errors import MultiplayerError, NetworkError
from nostalgia.multiplayer.peer_codec import (
    PeerDescription,
    build_peer_envelope,
    parse_peer_envelope,
)
from nostalgia.multiplayer.peer_stream import PeerStream
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
    connection = RTCPeerConnection(build_peer_configuration())
    stream = PeerStream(connection, connection.createDataChannel("nostalgia-" + purpose))
    try:
        async with asyncio.timeout(30):
            await connection.setLocalDescription(await connection.createOffer())
            description = connection.localDescription
            assert description is not None
            envelope = build_peer_envelope(
                room_secret, request_id, purpose, PeerDescription(description.sdp, description.type)
            )
            response = await asyncio.to_thread(
                http_client.send,
                "POST",
                base_url.rstrip("/") + f"/v1/rooms/{room_id}/peer",
                headers={"X-Room-Invite-Proof": proof, "Content-Type": "application/json"},
                body=json.dumps({"id": request_id, "purpose": purpose, "body": envelope}).encode(),
                max_bytes=96000,
            )
            if not response.is_ok:
                raise ConnectionError("peer negotiation unavailable")
            document = json.loads(response.body)
            if document["id"] != request_id:
                raise ValueError("peer answer scope mismatch")
            answer = parse_peer_envelope(room_secret, request_id, purpose, document["body"])
            if answer.description_kind != "answer":
                raise ValueError("invalid peer answer")
            await connection.setRemoteDescription(RTCSessionDescription(answer.sdp, "answer"))
            await stream.wait_open()
            return stream
    except (InvalidTag, ValueError, KeyError, TypeError) as exc:
        await stream.close()
        raise MultiplayerError(
            "Không xác thực được kết nối trực tiếp; hãy nhận lại lời mời."
        ) from exc
    except (ConnectionError, TimeoutError, NetworkError):
        await stream.close()
        raise
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
