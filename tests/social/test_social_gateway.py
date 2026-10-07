"""HTTPS thật: token phiên, proof đăng nhập, địa chỉ Google và trạng thái thu hồi."""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.net.http import HttpClient
from nostalgia.social.gateway import HttpSocialGateway
from nostalgia.social.parse import parse_snapshot


def snapshot_document() -> dict[str, object]:
    return {
        "account": {
            "account_id": "jun",
            "name": "Jun",
            "friend_code": "ABCDEF0123456789",
            "plus_until": 0,
        },
        "friends": [],
        "requests": [],
        "invitations": [],
    }


def test_google_consent_denied_stops_login(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    from nostalgia.social.model import GoogleLogin

    server_state.add("/v1/auth/google/poll", b'{"status":"denied"}')
    with pytest.raises(SocialError, match="hủy"):
        HttpSocialGateway(server.url(""), http_client).poll_login(
            GoogleLogin("attempt", "", 4200000000, "a" * 64)
        )


def test_browser_login_proof_and_no_token_in_url(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    server_state.add(
        "/v1/auth/google/start",
        json.dumps(
            {
                "login_id": "login",
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?state=state",
                "expires_at": int(time.time()) + 300,
            }
        ).encode(),
    )
    server_state.add(
        "/v1/auth/google/poll",
        b'{"status":"signed_in","access_token":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}',
    )
    gateway = HttpSocialGateway(server.url(""), http_client)
    login = gateway.start_login()
    body = json.loads(server_state.received_body("/v1/auth/google/start"))
    assert body == {"challenge": hashlib.sha256(login.verifier.encode()).hexdigest()}
    assert login.verifier not in login.authorization_url and login.verifier not in repr(login)
    access_token = gateway.poll_login(login)
    assert len(access_token) == 64
    assert not gateway.access_token  # Chỉ UI nhận kết quả hiện hành mới áp dụng phiên.
    assert json.loads(server_state.received_body("/v1/auth/google/poll")) == {
        "login_id": "login",
        "verifier": login.verifier,
    }
    gateway.access_token = access_token
    server_state.add("/v1/auth/encryption-key", b'{"registered":true}')
    server_state.add("/v1/me", json.dumps(snapshot_document()).encode())
    assert gateway.fetch_snapshot().account.plus_until == 0
    assert server_state.received_header("/v1/me", "Authorization") == "Bearer " + access_token
    server_state.add("/v1/me", b"{}", status=401)
    with pytest.raises(SessionRevoked):
        gateway.fetch_snapshot()


@pytest.mark.parametrize(
    "url",
    [
        "http://accounts.google.com",
        "https://accounts.google.com.evil.invalid/o/oauth2/v2/auth",
        "https://a:b@accounts.google.com/o/oauth2/v2/auth",
    ],
)
def test_phishing_google_url_rejected(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, url: str
) -> None:
    server_state.add(
        "/v1/auth/google/start",
        json.dumps(
            {"login_id": "login", "authorization_url": url, "expires_at": int(time.time()) + 300}
        ).encode(),
    )
    with pytest.raises(SocialError):
        HttpSocialGateway(server.url(""), http_client).start_login()


@pytest.mark.parametrize("status", [302, 403, 429, 503])
def test_error_not_accepted_as_account(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, status: int
) -> None:
    server_state.add("/v1/me", json.dumps(snapshot_document()).encode(), status=status)
    gateway = HttpSocialGateway(server.url(""), http_client)
    gateway.access_token = "a" * 64
    server_state.add("/v1/auth/encryption-key", b'{"registered":true}')
    with pytest.raises(SocialError):
        gateway.fetch_snapshot()


def test_untrusted_names_reject_markup() -> None:
    document = json.loads(json.dumps(snapshot_document()))
    document["account"]["name"] = '<img src="local">'
    with pytest.raises(SocialError):
        parse_snapshot(document)


def test_encrypted_invitation_gateway_roundtrip_over_https(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    server_state.add("/v1/auth/encryption-key", b'{"registered":true}')
    server_state.add("/v1/me", json.dumps(snapshot_document()).encode())
    host = HttpSocialGateway(server.url(""), http_client)
    host.access_token = "a" * 64
    host.fetch_snapshot()
    guest_document = snapshot_document()
    guest_document["account"] = {
        "account_id": "guest",
        "name": "Guest",
        "friend_code": "1234567890ABCDEF",
        "plus_until": 0,
    }
    server_state.add("/v1/me", json.dumps(guest_document).encode())
    guest = HttpSocialGateway(server.url(""), http_client)
    guest.access_token = "b" * 64
    guest.fetch_snapshot()
    public_key = json.loads(server_state.received_body("/v1/auth/encryption-key"))["public_key"]
    server_state.add("/v1/friends/guest/key", json.dumps({"public_key": public_key}).encode())
    server_state.add("/v1/invitations", b'{"invite_id":"invite"}')
    code = "ABCDEFABCDEFGHJKMN"
    host.send_invite("guest", code, "opaque-host-ticket", "World")
    document = json.loads(server_state.received_body("/v1/invitations"))
    assert code not in json.dumps(document) and "room_code" not in document
    assert document["room_id"] == "ABCDEF" and document["recipient_key"] == public_key
    server_state.add("/v1/invitations/invite/accept", json.dumps(document).encode())
    assert guest.accept_invite("invite") == code
