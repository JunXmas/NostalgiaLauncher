"""Mã hoá SDP và ràng buộc nó với đúng phòng, yêu cầu và mục đích kết nối."""

import base64
import json
import re
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


@dataclass(frozen=True, slots=True)
class PeerDescription:
    sdp: str
    description_kind: str


def build_peer_envelope(
    room_secret: str, request_id: str, purpose: str, description: PeerDescription
) -> str:
    nonce = secrets.token_bytes(12)
    payload = json.dumps({"sdp": description.sdp, "type": description.description_kind}).encode()
    encrypted = _cipher(room_secret).encrypt(nonce, payload, _scope(request_id, purpose))
    return base64.urlsafe_b64encode(nonce + encrypted).decode().rstrip("=")


def parse_peer_envelope(
    room_secret: str, request_id: str, purpose: str, encoded: str
) -> PeerDescription:
    if not 40 <= len(encoded) <= 90000:
        raise ValueError("invalid peer envelope length")
    payload = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    decoded = _cipher(room_secret).decrypt(payload[:12], payload[12:], _scope(request_id, purpose))
    document = json.loads(decoded)
    if not isinstance(document, dict):
        raise ValueError("invalid peer description")
    sdp, description_kind = document["sdp"], document["type"]
    if (
        not isinstance(sdp, str)
        or len(sdp) > 60000
        or description_kind not in ("offer", "answer")
        or len(re.findall(r"^m=", sdp, re.M)) != 1
        or not re.search(r"^m=application ", sdp, re.M)
        or not re.search(
            r"^a=fingerprint:sha-256 (?:[0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}\r?$", sdp, re.M
        )
    ):
        raise ValueError("invalid peer description")
    return PeerDescription(sdp, description_kind)


def _scope(request_id: str, purpose: str) -> bytes:
    if purpose not in ("game", "sync") or not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise ValueError("invalid peer scope")
    return ("nostalgia-peer-v1:" + purpose + ":" + request_id).encode()


def _cipher(room_secret: str) -> AESGCM:
    key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"nostalgia-peer-signalling-v1"
    ).derive(room_secret.encode())
    return AESGCM(key)
