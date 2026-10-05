"""Nos Client: config đọc/ghi và manager inject/remove."""

from __future__ import annotations

import json
from pathlib import Path

from nostalgia.instance.model import Instance
from nostalgia.instance.store import create_instance, load_instance
from nostalgia.nos_client.config import (
    NosClientConfig,
    load_nos_client_config,
    save_nos_client_config,
)
from nostalgia.nos_client.manager import MOD_JAR_PREFIX, inject_mod, remove_mod
from nostalgia.storage.paths import DataPaths


def make_paths(tmp_path: Path) -> DataPaths:
    return DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")


class TestNosClientConfig:
    def test_default_config_has_basic_huds_on(self) -> None:
        config = NosClientConfig()
        assert config.coords is True
        assert config.direction is True
        assert config.day is True
        assert config.fps is False
        assert config.ping is False
        assert config.cps is False

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "instance" / "my-world"
        game_dir.mkdir(parents=True)
        config = NosClientConfig(coords=False, fps=True, cps=True)

        save_nos_client_config(game_dir, config)
        loaded = load_nos_client_config(game_dir)

        assert loaded == config

    def test_load_missing_file_returns_default(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "nonexistent"
        game_dir.mkdir(parents=True)

        config = load_nos_client_config(game_dir)

        assert config == NosClientConfig()

    def test_load_corrupt_file_returns_default(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "broken"
        game_dir.mkdir(parents=True)
        config_dir = game_dir / "config"
        config_dir.mkdir()
        (config_dir / "nos-client.json").write_text("not json at all")

        config = load_nos_client_config(game_dir)

        assert config == NosClientConfig()

    def test_save_creates_config_directory(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "fresh"
        game_dir.mkdir(parents=True)

        save_nos_client_config(game_dir, NosClientConfig())

        assert (game_dir / "config" / "nos-client.json").is_file()


class TestModInject:
    def test_inject_copies_jar_to_mods(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "instance"
        game_dir.mkdir()
        # Tạo file jar giả.
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        fake_jar = cache_dir / f"{MOD_JAR_PREFIX}1.0.0.jar"
        fake_jar.write_bytes(b"PK fake jar content")

        result = inject_mod(fake_jar, game_dir)

        assert result.is_file()
        assert result.parent.name == "mods"
        assert result.read_bytes() == b"PK fake jar content"

    def test_inject_removes_old_version(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "instance"
        mods_dir = game_dir / "mods"
        mods_dir.mkdir(parents=True)
        # Bản cũ đã có.
        old_jar = mods_dir / f"{MOD_JAR_PREFIX}0.9.0.jar"
        old_jar.write_bytes(b"old")
        # Bản mới.
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        new_jar = cache_dir / f"{MOD_JAR_PREFIX}1.0.0.jar"
        new_jar.write_bytes(b"new")

        inject_mod(new_jar, game_dir)

        assert not old_jar.exists()
        assert (mods_dir / f"{MOD_JAR_PREFIX}1.0.0.jar").is_file()

    def test_remove_mod_cleans_up(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "instance"
        mods_dir = game_dir / "mods"
        mods_dir.mkdir(parents=True)
        jar = mods_dir / f"{MOD_JAR_PREFIX}1.0.0.jar"
        jar.write_bytes(b"content")

        remove_mod(game_dir)

        assert not jar.exists()

    def test_remove_mod_no_mods_dir_is_safe(self, tmp_path: Path) -> None:
        game_dir = tmp_path / "empty"
        game_dir.mkdir()

        # Không crash khi mods/ chưa tồn tại.
        remove_mod(game_dir)


class TestInstanceModelNosClient:
    def test_nos_client_enabled_defaults_to_false(self) -> None:
        instance = Instance(instance_id="test", version_id="1.20.1")
        assert instance.nos_client_enabled is False

    def test_nos_client_enabled_round_trip(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        instance = Instance(
            instance_id="nos-test",
            version_id="1.20.1",
            nos_client_enabled=True,
        )

        create_instance(paths, instance)
        loaded = load_instance(paths, "nos-test")

        assert loaded.nos_client_enabled is True

    def test_old_instance_without_nos_client_loads_as_disabled(self, tmp_path: Path) -> None:
        """Instance JSON cũ không có trường nos_client_enabled phải đọc thành False."""
        paths = make_paths(tmp_path)
        legacy_dir = paths.instances_dir / "legacy"
        legacy_dir.mkdir(parents=True)
        # Ghi JSON kiểu cũ, không có nos_client_enabled.
        (legacy_dir / "instance.json").write_text(
            json.dumps(
                {
                    "format": 1,
                    "instance_id": "legacy",
                    "version_id": "1.18.2",
                    "display_name": "Legacy World",
                }
            )
        )

        loaded = load_instance(paths, "legacy")

        assert loaded.nos_client_enabled is False
