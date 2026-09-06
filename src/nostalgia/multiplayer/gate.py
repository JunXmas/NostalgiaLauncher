"""Máy trạng thái xác thực cho MỘT stream, thuần (không I/O) để test kín.

Phía host (`HostGate`): nhận byte của joiner, trả byte cần gửi lại và phán quyết. Sau bắt tay,
byte đầu tiên còn phải là gói Handshake Minecraft (luật L4) mới được mở kết nối tới world.
Phía joiner (`JoinerGate`): gửi HELLO, kiểm proof của host, trả RESPONSE. Hỏng vì bất kỳ lý do
gì → `rejected`, không có đường lùi (luật L1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nostalgia.multiplayer import handshake
from nostalgia.multiplayer.mux import MAX_HANDSHAKE_PACKET, looks_like_minecraft_handshake

Verdict = Literal["pending", "accepted", "rejected"]


@dataclass(frozen=True, slots=True)
class GateStep:
    verdict: Verdict
    reply: bytes = b""  # gửi cho bên kia
    forward: bytes = b""  # byte Minecraft đã tới sau bắt tay, chuyển cho world/game


_REJECT = GateStep("rejected")
_WAIT = GateStep("pending")


class HostGate:
    def __init__(self, room_secret: str) -> None:
        self._room_secret = room_secret
        self._buffer = bytearray()
        self._host_nonce: bytes | None = None
        self._authenticated = False

    def feed(self, payload: bytes) -> GateStep:
        self._buffer += payload
        if len(self._buffer) > handshake.MAX_HANDSHAKE_BYTES + MAX_HANDSHAKE_PACKET:
            return _REJECT
        if self._authenticated:
            return self._check_minecraft()
        try:
            frame = handshake.parse_frame(bytes(self._buffer))
        except ValueError:
            return _REJECT
        if frame is None:
            return _WAIT
        self._buffer = bytearray(frame.trailing)
        if self._host_nonce is None:
            if frame.op != handshake.HELLO or not frame.fields:
                return _REJECT
            self._host_nonce = handshake.make_nonce()
            challenge = handshake.build_challenge(
                self._room_secret, frame.fields[0], self._host_nonce
            )
            return GateStep("pending", reply=challenge)
        if frame.op != handshake.RESPONSE or not frame.fields:
            return _REJECT
        expected = handshake.prove(self._room_secret, b"join", self._host_nonce)
        if not handshake.proof_matches(expected, frame.fields[0]):
            return _REJECT
        self._authenticated = True
        return self._check_minecraft()

    def _check_minecraft(self) -> GateStep:
        verdict = looks_like_minecraft_handshake(bytes(self._buffer))
        if verdict is None:
            return _WAIT
        if not verdict:
            return _REJECT
        forward, self._buffer = bytes(self._buffer), bytearray()
        return GateStep("accepted", forward=forward)


class JoinerGate:
    def __init__(self, room_secret: str) -> None:
        self._room_secret = room_secret
        self._join_nonce = handshake.make_nonce()
        self._buffer = bytearray()

    def hello(self) -> bytes:
        return handshake.build_hello(self._join_nonce)

    def feed(self, payload: bytes) -> GateStep:
        self._buffer += payload
        if len(self._buffer) > handshake.MAX_HANDSHAKE_BYTES:
            return _REJECT
        try:
            frame = handshake.parse_frame(bytes(self._buffer))
        except ValueError:
            return _REJECT
        if frame is None:
            return _WAIT
        if frame.op != handshake.CHALLENGE or len(frame.fields) < 2:
            return _REJECT
        host_nonce, host_proof = frame.fields[0], frame.fields[1]
        expected = handshake.prove(self._room_secret, b"host", self._join_nonce)
        if not handshake.proof_matches(expected, host_proof):
            return _REJECT  # host giả: không giữ secret → KHÔNG bắc cầu, không hạ cấp
        response = handshake.build_response(self._room_secret, host_nonce)
        return GateStep("accepted", reply=response, forward=frame.trailing)
