"""Chạy qua HTTPS thật: cập nhật từng nhánh, dùng cache khi mất mạng, giữ jar cũ khi lỗi."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nos_fixture import build_nos_jar, build_nos_release
from nostalgia.model.json_value import as_list, as_mapping
from nostalgia.net.http import HttpClient
from nostalgia.nos_client import release
from nostalgia.nos_client.installation import inject_mod
from nostalgia.nos_client.manager import sync_mod_cached
from nostalgia.storage.paths import DataPaths


@pytest.fixture(autouse=True)
def github_api(server: LocalHttpsServer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release, "GITHUB_API_BASE", server.url(""))


def test_updates_each_branch_and_reuses_valid_cache(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
) -> None:
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    old = build_nos_jar()
    modern = build_nos_jar("26.2", mod_version="0.5.0+mc26.2")
    old_route = server_state.add("/old.jar", old)
    new_route = server_state.add("/new.jar", modern)
    endpoint = server_state.add(
        "/repos/JunXmas/nos-client/releases",
        json.dumps(
            [
                build_nos_release("nos-client-0.5.0+mc26.2.jar", server.url(new_route), modern),
                build_nos_release("nos-client-0.4.2.jar", server.url(old_route), old),
            ]
        ).encode(),
    )
    legacy = sync_mod_cached(http_client, paths, "1.21.11")
    current = sync_mod_cached(http_client, paths, "1.21.11")
    assert legacy and legacy.read_bytes() == old
    assert current == legacy
    assert sync_mod_cached(http_client, paths, "1.21.11") == current
    assert server_state.routes[new_route].requests == 0
    game_dir = tmp_path / "game"
    inject_mod(legacy, game_dir)
    updated_body = build_nos_jar(mod_version="0.4.3")
    updated_route = server_state.add("/updated.jar", updated_body)
    updated = build_nos_release("nos-client-0.4.3.jar", server.url(updated_route), updated_body)
    server_state.routes[endpoint].body = json.dumps([updated]).encode()
    next_jar = sync_mod_cached(http_client, paths, "1.21.11")
    assert next_jar and next_jar.name == "nos-client-0.4.3.jar"
    inject_mod(next_jar, game_dir)
    assert [path.name for path in (game_dir / "mods").iterdir()] == [next_jar.name]
    assert legacy.exists() and current.exists()


def test_offline_cache_is_numeric_and_never_crosses_game_versions(
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
) -> None:
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    cache = paths.data_dir / "nos-client"
    cache.mkdir(parents=True)
    for mod_version in ("0.9.0", "0.10.0"):
        (cache / f"nos-client-{mod_version}.jar").write_bytes(
            build_nos_jar(mod_version=mod_version)
        )
    (cache / "nos-client-9.0.0.jar").write_bytes(build_nos_jar("26.2"))
    server_state.add("/repos/JunXmas/nos-client/releases", b"[]")
    cached = sync_mod_cached(http_client, paths, "1.21.11")
    assert cached and cached.name == "nos-client-0.10.0.jar"
    assert sync_mod_cached(http_client, paths, "26.2") is None


@pytest.mark.parametrize("failure", ["wrong-game", "bad-digest", "offline"])
def test_failed_update_preserves_known_good_cache(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    failure: str,
) -> None:
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    cache = paths.data_dir / "nos-client"
    cache.mkdir(parents=True)
    previous = cache / "nos-client-0.4.2.jar"
    previous.write_bytes(build_nos_jar())
    body = build_nos_jar("26.2" if failure == "wrong-game" else "1.21.11", mod_version="0.4.3")
    url = server_state.add("/latest.jar", body)
    document = build_nos_release("nos-client-0.4.3.jar", server.url(url), body)
    if failure == "bad-digest":
        as_mapping(as_list(document["assets"])[0])["digest"] = "sha256:" + "0" * 64
        # Jar cùng tên đã cache cũng sai băm: không được trả lại nó làm fallback.
        invalid = cache / "1.21.11" / ("0" * 64) / "nos-client-0.4.3.jar"
        invalid.parent.mkdir(parents=True)
        invalid.write_bytes(body)
    endpoint = server_state.add(
        "/repos/JunXmas/nos-client/releases", json.dumps([document]).encode()
    )
    if failure == "offline":
        server_state.routes[endpoint].status = 404
    assert sync_mod_cached(http_client, paths, "1.21.11") == previous
    assert previous.read_bytes() == build_nos_jar()
    assert not list(cache.glob(".download-*"))


def test_corrupt_cached_jar_is_downloaded_again(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
) -> None:
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    body = build_nos_jar()
    cached = (
        paths.data_dir
        / "nos-client"
        / "1.21.11"
        / hashlib.sha256(body).hexdigest()
        / "nos-client-0.4.2.jar"
    )
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"X" * len(body))
    url = server_state.add("/client.jar", body)
    server_state.add(
        "/repos/JunXmas/nos-client/releases",
        json.dumps(
            [
                build_nos_release(cached.name, server.url(url), body),
            ]
        ).encode(),
    )
    assert sync_mod_cached(http_client, paths, "1.21.11") == cached
    assert cached.read_bytes() == body
    assert server_state.routes[url].requests == 1


def test_unsupported_game_does_not_query_github(
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
) -> None:
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    assert sync_mod_cached(http_client, paths, "1.8.9") is None
    assert not paths.data_dir.exists()
    assert not server_state.routes
