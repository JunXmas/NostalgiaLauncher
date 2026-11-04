"""Digest/SHA256SUMS, phiên bản số và phân trang phải hoạt động qua HTTP client thật."""

import hashlib
import json
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nos_fixture import build_nos_jar, build_nos_release
from nostalgia.errors import Cancelled
from nostalgia.model.json_value import JsonValue, as_list, as_mapping
from nostalgia.net.http import HttpClient
from nostalgia.nos_client import release
from nostalgia.nos_client.manager import sync_mod_cached
from nostalgia.nos_client.release import fetch_compatible_release, parse_mod_releases
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.paths import DataPaths


@pytest.mark.parametrize("checksum", ["valid", "missing", "invalid"])
def test_legacy_release_requires_valid_sha256sums(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checksum: str,
) -> None:
    monkeypatch.setattr(release, "GITHUB_API_BASE", server.url(""))
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    body = build_nos_jar()
    jar_url = server_state.add("/client.jar", body)
    document = build_nos_release("nos-client-0.4.2.jar", server.url(jar_url), body)
    as_mapping(as_list(document["assets"])[0]).pop("digest")
    if checksum != "missing":
        digest = hashlib.sha256(body).hexdigest() if checksum == "valid" else "z" * 64
        sums_url = server_state.add("/SHA256SUMS", f"{digest}  nos-client-0.4.2.jar\n".encode())
        as_list(document["assets"]).append(
            {"name": "SHA256SUMS", "browser_download_url": server.url(sums_url)}
        )
    server_state.add("/repos/JunXmas/nos-client/releases", json.dumps([document]).encode())
    cached = sync_mod_cached(http_client, paths, "1.21.11")
    if checksum == "valid":
        assert cached and cached.read_bytes() == body
        assert cached.parent.name == hashlib.sha256(body).hexdigest()
    else:
        assert cached is None
        assert server_state.routes[jar_url].requests == 0


def test_numeric_version_beats_asset_and_release_order() -> None:
    body = build_nos_jar()
    document: JsonValue = [
        build_nos_release(f"nos-client-{number}.jar", "https://example.test/a", body)
        for number in ("0.9.0", "0.4.2", "0.10.0")
    ]
    assert parse_mod_releases(document, "1.21.11")[0].file_name == "nos-client-0.10.0.jar"


def test_fetches_next_page_and_stays_bounded(
    http_client: HttpClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    document = build_nos_release("nos-client-0.4.2.jar", "https://example.test/a", build_nos_jar())

    def fetch(_self: HttpClient, url: str, **_kwargs: object) -> bytes:
        calls.append(url)
        return json.dumps([{}] * 20 if "page=1" in url else [document]).encode()

    monkeypatch.setattr(HttpClient, "fetch_bytes", fetch)
    found = fetch_compatible_release(http_client, "1.21.11")
    assert found and found.file_name == "nos-client-0.4.2.jar"
    assert len(calls) == 2 and "page=2" in calls[-1]
    calls.clear()

    def empty_pages(_self: HttpClient, url: str, **_kwargs: object) -> bytes:
        calls.append(url)
        return json.dumps([{}] * 20).encode()

    monkeypatch.setattr(HttpClient, "fetch_bytes", empty_pages)
    assert fetch_compatible_release(http_client, "1.21.11") is None
    assert len(calls) == 5


def test_cancellation_is_not_swallowed_as_an_offline_fallback(
    http_client: HttpClient,
    tmp_path: Path,
) -> None:
    cancel_token = CancelToken()
    cancel_token.cancel()
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    with pytest.raises(Cancelled):
        sync_mod_cached(http_client, paths, "1.21.11", cancel_token=cancel_token)
    assert not paths.data_dir.exists()


def test_verified_legacy_cache_migrates_without_downloading_again(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release, "GITHUB_API_BASE", server.url(""))
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    body = build_nos_jar()
    legacy = paths.data_dir / "nos-client/nos-client-0.4.2.jar"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(body)
    jar_url = server_state.add("/client.jar", body)
    server_state.add(
        "/repos/JunXmas/nos-client/releases",
        json.dumps(
            [
                build_nos_release(legacy.name, server.url(jar_url), body),
            ]
        ).encode(),
    )
    cached = sync_mod_cached(http_client, paths, "1.21.11")
    assert cached and cached.parent.name == hashlib.sha256(body).hexdigest()
    assert cached.read_bytes() == body
    assert server_state.routes[jar_url].requests == 0


def test_bad_legacy_cache_cannot_bypass_release_digest(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release, "GITHUB_API_BASE", server.url(""))
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    body = build_nos_jar()
    legacy = paths.data_dir / "nos-client/nos-client-0.4.2.jar"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(body)
    jar_url = server_state.add("/client.jar", body)
    document = build_nos_release(legacy.name, server.url(jar_url), body)
    as_mapping(as_list(document["assets"])[0])["digest"] = "sha256:" + "0" * 64
    endpoint = server_state.add(
        "/repos/JunXmas/nos-client/releases", json.dumps([document]).encode()
    )
    assert sync_mod_cached(http_client, paths, "1.21.11") is None
    server_state.routes[endpoint].status = 404
    assert sync_mod_cached(http_client, paths, "1.21.11") is None
