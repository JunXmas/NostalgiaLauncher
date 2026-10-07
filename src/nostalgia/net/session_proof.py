"""Bind API requests to a Google session key; a copied bearer alone cannot sign them.

Private seeds stay in memory or the approved OS credential store. This is possession
proof, not hardware attestation: copying both credentials remains possible.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import threading
import time

_lock = threading.Lock()
_seeds: dict[str, str] = {}


def public_key(seed: str) -> str:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    return (
        Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
        .hex()
    )


def register_session(access_token: str, seed: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", access_token) or not re.fullmatch(
        r"[0-9a-f]{64}", seed
    ):
        return
    with _lock:
        _seeds[access_token] = seed
        while len(_seeds) > 8:
            del _seeds[next(iter(_seeds))]


def session_seed(access_token: str) -> str:
    with _lock:
        return _seeds.get(access_token, "")


def forget_session(access_token: str) -> None:
    with _lock:
        _seeds.pop(access_token, None)


def proof_headers(access_token: str, method: str, url: str, body: bytes | None) -> dict[str, str]:
    seed = session_seed(access_token)
    if not seed:
        return {}
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    claims = {
        "v": 1,
        "iat": int(time.time()),
        "jti": secrets.token_hex(16),
        "htm": method,
        "htu": url,
        "ath": hashlib.sha256(access_token.encode()).hexdigest(),
        "bht": hashlib.sha256(body or b"").hexdigest(),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).rstrip(
        b"="
    )
    signature = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed)).sign(encoded).hex()
    return {"Nostalgia-Proof": encoded.decode() + "." + signature}
