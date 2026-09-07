"""Ely.by giả + trang phát hành authlib-injector giả trên máy chủ HTTPS cục bộ."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS, AuthEndpoints

ELY_UUID = "8f4a0d3e-1c2b-3a4d-9e5f-6a7b8c9d0e1f"
ELY_NAME = "JunBob"
ACCESS_TOKEN = "ely-access-1"
REFRESHED_TOKEN = "ely-access-2"
INJECTOR_JAR = b"PK\x03\x04 authlib-injector gia"
API_METADATA = b'{"meta":{"serverName":"Ely.by"},"skinDomains":["ely.by"]}'


def publish(server: LocalHttpsServer, state: ServerState) -> AuthEndpoints:
    state.add(
        "/ely/auth/authenticate",
        json.dumps(
            {
                "accessToken": ACCESS_TOKEN,
                "clientToken": "ignored-by-client",
                "selectedProfile": {"id": ELY_UUID.replace("-", ""), "name": ELY_NAME},
            }
        ).encode(),
    )
    state.add(
        "/ely/auth/refresh",
        json.dumps(
            {
                "accessToken": REFRESHED_TOKEN,
                "selectedProfile": {"id": ELY_UUID.replace("-", ""), "name": ELY_NAME},
            }
        ).encode(),
    )
    jar_url = server.url(state.add("/authlib/authlib-injector-9.9.9.jar", INJECTOR_JAR))
    state.add(
        "/authlib/latest.json",
        json.dumps(
            {
                "version": "9.9.9",
                "download_url": jar_url,
                "checksums": {"sha256": hashlib.sha256(INJECTOR_JAR).hexdigest()},
            }
        ).encode(),
    )
    state.add("/ely/api/authlib-injector", API_METADATA)
    return replace(
        DEFAULT_AUTH_ENDPOINTS,
        ely_auth_url=server.url("/ely/auth"),
        ely_authlib_root_url=server.url("/ely/api/authlib-injector"),
        authlib_injector_latest_url=server.url("/authlib/latest.json"),
    )
