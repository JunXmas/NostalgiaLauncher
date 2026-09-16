"""Test cho facade/importing.py — ImportOperations."""

from __future__ import annotations

from pathlib import Path

import pytest

from nostalgia.facade.importing import ImportOperations, _copy_game_data
from nostalgia.importing.launchers import Found


class TestCopyGameData:
    """_copy_game_data copy đúng thư mục và bỏ qua thứ không cần."""

    def test_copies_mods(self, tmp_path: Path) -> None:
        """mods/ được copy nguyên vẹn."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        mods = source / "mods"
        mods.mkdir(parents=True)
        (mods / "test.jar").write_bytes(b"mod content")
        target.mkdir()

        _copy_game_data(source, target)

        assert (target / "mods" / "test.jar").read_bytes() == b"mod content"

    def test_copies_config(self, tmp_path: Path) -> None:
        """config/ được copy."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        config = source / "config"
        config.mkdir(parents=True)
        (config / "mod.toml").write_text("key = 'value'")
        target.mkdir()

        _copy_game_data(source, target)

        assert (target / "config" / "mod.toml").read_text() == "key = 'value'"

    def test_copies_saves(self, tmp_path: Path) -> None:
        """saves/ được copy (thế giới của người chơi)."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        saves = source / "saves" / "world1"
        saves.mkdir(parents=True)
        (saves / "level.dat").write_bytes(b"nbt")
        target.mkdir()

        _copy_game_data(source, target)

        assert (target / "saves" / "world1" / "level.dat").read_bytes() == b"nbt"

    def test_copies_options_txt(self, tmp_path: Path) -> None:
        """options.txt (file, không phải thư mục) được copy."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        source.mkdir(parents=True)
        (source / "options.txt").write_text("fov:80")
        target.mkdir()

        _copy_game_data(source, target)

        assert (target / "options.txt").read_text() == "fov:80"

    def test_skip_missing(self, tmp_path: Path) -> None:
        """Thư mục không tồn tại → bỏ qua, không crash."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        source.mkdir()
        target.mkdir()

        _copy_game_data(source, target)  # không crash

    def test_does_not_copy_versions(self, tmp_path: Path) -> None:
        """versions/ KHÔNG được copy — kho chung dùng riêng."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        versions = source / "versions" / "1.21"
        versions.mkdir(parents=True)
        (versions / "1.21.json").write_text("{}")
        target.mkdir()

        _copy_game_data(source, target)

        assert not (target / "versions").exists()


class TestFoundDataclass:
    """Found là frozen dataclass với đúng field."""

    def test_fields(self) -> None:
        found = Found(
            launcher="PrismLauncher",
            instance_name="Test",
            game_dir=Path("/game"),
            game_version="1.21",
            loader_kind="fabric",
        )
        assert found.launcher == "PrismLauncher"
        assert found.loader_kind == "fabric"
