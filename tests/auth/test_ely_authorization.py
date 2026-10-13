"""Chuyển hướng Ely.by thật đặt client_id trong đường dẫn, không đặt trong query."""

from urllib.parse import parse_qs, urlsplit

import pytest

from fake_ely import publish_web
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.auth.ely_redirect import resolve_ely_authorization_query
from nostalgia.auth.ely_web import sign_in_ely_web
from nostalgia.errors import AccountError
from nostalgia.net.http import HttpClient


def test_ely_client_id_is_added_when_only_present_in_the_redirect_path(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    server_state.add(
        "/elysite/authorization/login",
        b"",
        status=302,
        location=server.url("/elyweb/oauth2/v1/ely")
        + "?scope=account_info&state=opaque%2Bvalue&response_type=code&redirect_uri="
        + server.url("/elysite/authorization/oauth"),
        response_headers=(("Set-Cookie", "PHPSESSID=sess-1; path=/; httponly"),),
    )

    sign_in_ely_web(http_client, "jun@example.com", "password", endpoints=endpoints)

    query = parse_qs(urlsplit(server_state.received_path("/elyweb/api/oauth2/v1/complete")).query)
    assert query["client_id"] == ["ely"]
    assert query["state"] == ["opaque+value"]
    assert query["scope"] == ["account_info"]
    assert query["redirect_uri"] == [server.url("/elysite/authorization/oauth")]


@pytest.mark.parametrize("path", ["/oauth2/v1/ely", "/api/oauth2/v1/ely"])
def test_existing_ely_client_id_and_empty_opaque_parameters_are_preserved(path: str) -> None:
    query = resolve_ely_authorization_query(
        "https://account.ely.by" + path + "?client_id=ely&state=&scope=account_info",
        "https://account.ely.by",
    )
    assert parse_qs(query, keep_blank_values=True) == {
        "client_id": ["ely"],
        "state": [""],
        "scope": ["account_info"],
    }


@pytest.mark.parametrize(
    "redirect",
    [
        "https://other.example/oauth2/v1/ely",
        "http://account.ely.by/oauth2/v1/ely",
        "https://account.ely.by/oauth2/v1/other",
        "https://account.ely.by/oauth2/v1/ely?client_id=other",
        "https://account.ely.by/oauth2/v1/ely?client_id=ely&client_id=ely",
        "https://account.ely.by@other.example/oauth2/v1/ely",
    ],
)
def test_unexpected_oauth_redirect_is_rejected(redirect: str) -> None:
    with pytest.raises(AccountError):
        resolve_ely_authorization_query(redirect, "https://account.ely.by")
