"""User configuration survives edits; malformed values and paths cannot escape the server."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from nostalgia.errors import NostalgiaError, ServerError
from server_fixture import ServerAccountFixture, server_launcher


def test_known_fields_update_unknown_vendor_settings_comments_survive(tmp_path: Path) -> None:
    launcher, _http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Host", "paper", "1.21.1", "132")
    directory = manager.directory(server.server_id)
    properties_file = directory / "server.properties"
    properties_file.write_text(
        properties_file.read_text() + "# custom server tuning\ncustom.option=retained\n"
    )
    properties = manager.properties(server.server_id)
    values = dict(properties.values) | {"server-port": "25570", "max-players": "12", "pvp": "false"}
    manager.save_settings(
        server.server_id,
        replace(properties, values=tuple(values.items()), eula_accepted=True),
        4096,
    )
    assert "# custom server tuning\ncustom.option=retained" in properties_file.read_text()
    assert manager.server(server.server_id).heap_megabytes == 4096
    assert dict(manager.properties(server.server_id).values)["server-port"] == "25570"
    assert manager.properties(server.server_id).eula_accepted
    for property_key, value in (
        ("server-port", "1"),
        ("max-players", "0"),
        ("motd", "hello\nadmin=true"),
        ("difficulty", "impossible"),
    ):
        invalid = replace(
            properties, values=tuple((dict(properties.values) | {property_key: value}).items())
        )
        before = properties_file.read_bytes()
        with pytest.raises(ServerError):
            manager.save_settings(server.server_id, invalid, 2048)
        assert properties_file.read_bytes() == before


def test_advanced_config_is_bounded_and_symlinks_traversal_rejected(tmp_path: Path) -> None:
    launcher, _http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Host", "paper", "1.21.1", "132")
    directory = manager.directory(server.server_id)
    plugin_dir = directory / "plugins" / "Example"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "config.yml").write_text("enabled: true\n")
    assert "plugins/Example/config.yml" in manager.config_files(server.server_id)
    manager.save_config(server.server_id, "plugins/Example/config.yml", "enabled: false\n")
    assert manager.read_config(server.server_id, "plugins/Example/config.yml") == "enabled: false\n"
    with pytest.raises(ServerError):
        manager.save_config(server.server_id, "plugins/Example/config.yml", "x" * 256_001)
    with pytest.raises(ServerError):
        manager.save_config(server.server_id, "nostalgia-server.json", "{}")
    with pytest.raises(ServerError):
        manager.save_config(server.server_id, "../outside.properties", "altered")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.yml").write_text("untouched")
    try:
        (directory / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(NostalgiaError):
        manager.read_config(server.server_id, "linked/secret.yml")
    assert (outside / "secret.yml").read_text() == "untouched"


def test_trash_preserves_whole_world_for_manual_restore(tmp_path: Path) -> None:
    launcher, _http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Host", "paper", "1.21.1", "132")
    directory = manager.directory(server.server_id)
    (directory / "world").mkdir()
    (directory / "world" / "level.dat").write_bytes(b"real world data")
    manager.trash(server.server_id)
    assert manager.list_servers() == ()
    paths = list(launcher.paths.data_dir.glob("servers/.trash/*/world/level.dat"))
    assert len(paths) == 1 and paths[0].read_bytes() == b"real world data"


def test_escaped_motd_round_trips_and_world_configs_are_not_scanned(tmp_path: Path) -> None:
    launcher, _http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Host", "paper", "1.21.1", "132")
    directory = manager.directory(server.server_id)
    properties_file = directory / "server.properties"
    properties_file.write_text(r"motd=Ch\u00e0o C:\\Minecraft" + "\n")
    properties = manager.properties(server.server_id)
    assert dict(properties.values)["motd"] == "Chào C:\\Minecraft"
    manager.save_settings(server.server_id, properties, 2048)
    assert manager.properties(server.server_id).values == properties.values
    world = directory / "custom-world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"world")
    (world / "private.json").write_text("{}")
    libraries = directory / "libraries"
    libraries.mkdir()
    (libraries / "cache.json").write_text("{}")
    assert "custom-world/private.json" not in manager.config_files(server.server_id)
    assert "libraries/cache.json" not in manager.config_files(server.server_id)
