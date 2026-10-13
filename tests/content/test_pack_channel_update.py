"""A remote pack updates an unchanged launcher, with checksum and player-data protection."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from builtin_update_fixture import Upgrade, jar
from builtin_update_fixture import upgrade as upgrade
from fabric_fixture import LOADER_VERSION
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer
from nostalgia.content.pack_channel import cached_channel, parse_channel
from nostalgia.errors import ContentError, IntegrityError
from nostalgia.facade import preset_updates
from nostalgia.model.json_value import JsonValue


def publish_channel(
    upgrade: Upgrade, server: LocalHttpsServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Upgrade:
    launcher, instance, host, state = upgrade
    payload = (tmp_path / "new.mrpack").read_bytes()
    state.add("/channel/pack.mrpack", payload)
    document = {
        "format": 1,
        "preset": "forgotten-worlds",
        "version": "1.0.2",
        "minecraft": VERSION_ID,
        "fabric-loader": LOADER_VERSION,
        "url": server.url("/channel/pack.mrpack"),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }
    state.add("/channel/latest.json", json.dumps(document).encode())
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints, builtin_modpack_feed=server.url("/channel/latest.json")
        ),
    )
    monkeypatch.setattr(
        preset_updates, "load_forgotten_worlds_pack", lambda: tmp_path / "old.mrpack"
    )
    return launcher, instance, host, state


def test_remote_update_preserves_data_without_changing_bundled_pack(
    upgrade: Upgrade, server: LocalHttpsServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, instance, host, state = publish_channel(upgrade, server, tmp_path, monkeypatch)
    game_dir = launcher.instance_game_dir(instance)
    protected = {
        "saves/factory/level.dat": b"factory",
        "options.txt": b"my controls",
        "servers.dat": b"my servers",
        "config/player.toml": b"my config",
        "mods/personal.jar": jar("personal"),
    }
    for relative, payload in protected.items():
        target = game_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    bundled_before = (tmp_path / "old.mrpack").read_bytes()
    launcher.refresh_builtin_modpack()
    status = launcher.builtin_pack_status(instance)
    assert status and status.update_available and status.available_version == "1.0.2"
    requests = state.request_count("/channel/latest.json")
    launcher.builtin_pack_status(instance)
    assert state.request_count("/channel/latest.json") == requests
    assert launcher.update_builtin_modpack(instance.instance_id, allowed_hosts=(host,)) == instance
    assert (game_dir / "mods/jei.jar").read_bytes() == jar("jei")
    assert all(
        (game_dir / relative).read_bytes() == payload for relative, payload in protected.items()
    )
    assert (tmp_path / "old.mrpack").read_bytes() == bundled_before
    status = launcher.builtin_pack_status(instance)
    assert status and not status.update_available


def test_bad_remote_pack_cannot_modify_instance(
    upgrade: Upgrade, server: LocalHttpsServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, instance, host, state = publish_channel(upgrade, server, tmp_path, monkeypatch)
    launcher.refresh_builtin_modpack()
    state.add("/channel/pack.mrpack", b"tampered")
    game_dir = launcher.instance_game_dir(instance)
    before = {
        p.relative_to(game_dir): p.read_bytes()
        for p in game_dir.rglob("*")
        if p.is_file() and p.name != ".nostalgia-sync.lock"
    }
    with pytest.raises(IntegrityError):
        launcher.update_builtin_modpack(instance.instance_id, allowed_hosts=(host,))
    assert before == {
        p.relative_to(game_dir): p.read_bytes()
        for p in game_dir.rglob("*")
        if p.is_file() and p.name != ".nostalgia-sync.lock"
    }


def test_remote_channel_cannot_roll_back_cached_version(
    upgrade: Upgrade, server: LocalHttpsServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, _instance, _host, state = publish_channel(upgrade, server, tmp_path, monkeypatch)
    launcher.refresh_builtin_modpack()
    body = json.loads(state.routes["/channel/latest.json"].body)
    body["version"] = "1.0.1"
    state.add("/channel/latest.json", json.dumps(body).encode())
    with pytest.raises(ContentError, match="cũ hơn"):
        launcher.refresh_builtin_modpack()
    channel = cached_channel(launcher.paths)
    assert channel and channel.version_id == "1.0.2"


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "http://host/pack"),
        ("url", "https://user:password@host/pack"),
        ("size", True),
        ("sha256", "incorrect"),
        ("preset", "another-pack"),
    ],
)
def test_invalid_channel_is_rejected(field: str, value: JsonValue) -> None:
    document: dict[str, JsonValue] = {
        "format": 1,
        "preset": "forgotten-worlds",
        "version": "1.0.3",
        "minecraft": "1.21.11",
        "fabric-loader": "0.19.5",
        "url": "https://github.com/pack.mrpack",
        "sha256": "a" * 64,
        "size": 123,
    }
    document[field] = value
    with pytest.raises(ContentError):
        parse_channel(document)
