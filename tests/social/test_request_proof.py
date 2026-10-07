"""Possession signatures bind every Premium adapter, including raw modpack upload bytes."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import ContentError
from nostalgia.modrepair.gateway import HttpRepairGateway
from nostalgia.modrepair.model import RepairPlan
from nostalgia.multiplayer.sync_gateway import HttpRoomSyncGateway
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient
from nostalgia.net.session_proof import forget_session, proof_headers, public_key, register_session
from nostalgia.payment.gateway import HttpPaymentGateway
from nostalgia.server.gateway import HttpServerGateway
from nostalgia.social.gateway import HttpSocialGateway
from payment_fixture import offer_document

SEED = "1a" * 32
ACCESS_TOKEN = "proof_test_" + "a" * 54


def verify(value: str, method: str, url: str, payload: bytes) -> dict[str, object]:
    encoded, signature = value.split(".")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key(SEED))).verify(
        bytes.fromhex(signature), encoded.encode()
    )
    claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    assert claims["htm"] == method and claims["htu"] == url
    assert claims["ath"] == hashlib.sha256(ACCESS_TOKEN.encode()).hexdigest()
    assert claims["bht"] == hashlib.sha256(payload).hexdigest()
    return dict(claims)


def test_unsigned_copied_bearer_has_no_proof_and_each_signed_request_has_fresh_nonce() -> None:
    forget_session(ACCESS_TOKEN)
    assert not proof_headers(ACCESS_TOKEN, "GET", "https://accounts.test/v1/me", None)
    register_session(ACCESS_TOKEN, SEED)
    try:
        nonces = set()
        for _index in range(32):
            value = proof_headers(ACCESS_TOKEN, "GET", "https://accounts.test/v1/me", None)
            claims = verify(value["Nostalgia-Proof"], "GET", "https://accounts.test/v1/me", b"")
            nonces.add(claims["jti"])
        assert len(nonces) == 32
    finally:
        forget_session(ACCESS_TOKEN)


def test_social_server_payment_and_repair_send_bound_signature_over_real_https(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    register_session(ACCESS_TOKEN, SEED)
    try:
        server_state.add("/v1/friends/peer/messages", b'{"sent":true}')
        gateway = HttpSocialGateway(server.url(""), http_client)
        gateway.access_token = ACCESS_TOKEN
        gateway.send_message("peer", "Xin chào", "message")
        server_state.add(
            "/v1/servers/access",
            b'{"plan_name":"Pro","server_hosting":true,"hosting_mode":"local","maximum_running":1}',
        )
        HttpServerGateway(server.url(""), http_client, ACCESS_TOKEN).authorize()
        server_state.add("/v1/plus/offer", json.dumps(offer_document()).encode())
        assert (
            HttpPaymentGateway(server.url(""), ACCESS_TOKEN, http_client).fetch_offer().amount > 0
        )
        path = "/v1/plus/repair/" + "a" * 64 + "/authorize"
        server_state.add(path, b'{"authorized":true}')
        plan = RepairPlan("a" * 64, "b" * 64, 4200000000, (), ())
        HttpRepairGateway(server.url(""), ACCESS_TOKEN, http_client).authorize(plan)
        for route in ["/v1/friends/peer/messages", "/v1/servers/access", "/v1/plus/offer", path]:
            method = "GET" if route in ("/v1/servers/access", "/v1/plus/offer") else "POST"
            verify(
                server_state.received_header(route, "Nostalgia-Proof"),
                method,
                server.url(route),
                server_state.received_body(route),
            )
        server_state.add(path, b"{}", status=409)
        with pytest.raises(ContentError):
            HttpRepairGateway(server.url(""), ACCESS_TOKEN, http_client).authorize(plan)
    finally:
        forget_session(ACCESS_TOKEN)


def test_modpack_manifest_file_and_commit_are_signed_but_free_guest_sends_no_token(
    tmp_path: Path, server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    payload = b"raw modpack bytes"
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/a.jar").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    sync_file = SyncFile("mods/a.jar", digest, len(payload))
    manifest = SyncManifest("Pack", "1.20.1", "forge", "47.4.23", (sync_file,))
    path = "/v1/rooms/ABCDEF/sync"
    for route in [path, path + "/files/" + digest, path + "/commit"]:
        server_state.add(route, b"{}")
    register_session(ACCESS_TOKEN, SEED)
    try:
        HttpRoomSyncGateway(server.url(""), http_client, ACCESS_TOKEN).publish(
            "ABCDEFABCDEFGHJKMN", "host-ticket", SyncSnapshot(manifest, tmp_path)
        )
        for route in [path, path + "/files/" + digest, path + "/commit"]:
            verify(
                server_state.received_header(route, "Nostalgia-Proof"),
                "PUT" if "/files/" in route else "POST",
                server.url(route),
                server_state.received_body(route),
            )
        server_state.add(path, b"{}", status=404)
        assert (
            HttpRoomSyncGateway(server.url(""), http_client).resolve("ABCDEFABCDEFGHJKMN") is None
        )
        assert not server_state.received_header(path, "Authorization")
        assert not server_state.received_header(path, "Nostalgia-Proof")
    finally:
        forget_session(ACCESS_TOKEN)
