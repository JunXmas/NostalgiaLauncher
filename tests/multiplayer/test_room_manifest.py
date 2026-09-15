"""Test cho multiplayer/room_manifest.py — build, diff, và serialise manifest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.multiplayer.room_manifest import (
    MANIFEST_VERSION,
    FileEntry,
    Manifest,
    ManifestDiff,
    build_manifest,
    diff_manifest,
    manifest_from_dict,
    manifest_to_dict,
    safe_paths_only,
)


class TestFileEntry:
    def test_frozen(self) -> None:
        file_record = FileEntry(relative_path="mods/mod.jar", sha1="abc123", size=1024)
        with pytest.raises(AttributeError):
            file_record.sha1 = "def456"  # type: ignore[misc]


class TestBuildManifest:
    """build_manifest quét thư mục và băm file."""

    def test_empty_game_dir(self, tmp_path: Path) -> None:
        """game_dir rỗng → manifest rỗng."""
        manifest = build_manifest(tmp_path, "1.21", "fabric")
        assert manifest.manifest_version == MANIFEST_VERSION
        assert manifest.game_version == "1.21"
        assert manifest.loader_kind == "fabric"
        assert manifest.entries == ()

    def test_scans_mods(self, tmp_path: Path) -> None:
        """Tạo file trong mods/ → manifest chứa đúng entry."""
        mods = tmp_path / "mods"
        mods.mkdir()
        (mods / "test-mod.jar").write_bytes(b"fake mod content")
        (mods / ".hidden").write_bytes(b"should be skipped")

        manifest = build_manifest(tmp_path, "1.21", "fabric")
        paths = {e.relative_path for e in manifest.entries}
        assert "mods/test-mod.jar" in paths
        assert "mods/.hidden" not in paths  # file ẩn bị bỏ qua

    def test_scans_config(self, tmp_path: Path) -> None:
        """config/ cũng được quét."""
        config = tmp_path / "config"
        config.mkdir()
        (config / "mod.toml").write_text("key = 'value'")

        manifest = build_manifest(tmp_path, "1.21", "vanilla")
        paths = {e.relative_path for e in manifest.entries}
        assert "config/mod.toml" in paths

    def test_skips_saves(self, tmp_path: Path) -> None:
        """saves/ KHÔNG nằm trong SCANNED_DIRS → không quét."""
        saves = tmp_path / "saves"
        saves.mkdir()
        (saves / "world1" / "level.dat").parent.mkdir(parents=True)
        (saves / "world1" / "level.dat").write_bytes(b"nbt")

        manifest = build_manifest(tmp_path, "1.21", "vanilla")
        paths = {e.relative_path for e in manifest.entries}
        assert not any(p.startswith("saves/") for p in paths)

    def test_sha1_not_empty(self, tmp_path: Path) -> None:
        """Mỗi entry có sha1 khác rỗng."""
        mods = tmp_path / "mods"
        mods.mkdir()
        (mods / "test.jar").write_bytes(b"content")

        manifest = build_manifest(tmp_path, "1.21", "vanilla")
        for manifest_entry in manifest.entries:
            assert manifest_entry.sha1
            assert len(manifest_entry.sha1) == 40  # sha1 hex


class TestDiffManifest:
    """diff_manifest tìm khác biệt đúng."""

    def test_identical(self) -> None:
        """Hai manifest giống nhau → diff rỗng."""
        entries = (FileEntry("mods/a.jar", "abc", 100),)
        local = Manifest(MANIFEST_VERSION, "1.21", "fabric", entries)
        remote = Manifest(MANIFEST_VERSION, "1.21", "fabric", entries)
        diff = diff_manifest(local, remote)
        assert diff.to_download == ()
        assert diff.to_delete == ()

    def test_new_file(self) -> None:
        """Remote có file mới → to_download."""
        local = Manifest(MANIFEST_VERSION, "1.21", "fabric", ())
        remote_entries = (FileEntry("mods/new.jar", "abc", 100),)
        remote = Manifest(MANIFEST_VERSION, "1.21", "fabric", remote_entries)
        diff = diff_manifest(local, remote)
        assert len(diff.to_download) == 1
        assert diff.to_download[0].relative_path == "mods/new.jar"
        assert diff.to_delete == ()

    def test_deleted_file(self) -> None:
        """Local có file mà remote không có → to_delete."""
        local_entries = (FileEntry("mods/old.jar", "abc", 100),)
        local = Manifest(MANIFEST_VERSION, "1.21", "fabric", local_entries)
        remote = Manifest(MANIFEST_VERSION, "1.21", "fabric", ())
        diff = diff_manifest(local, remote)
        assert diff.to_download == ()
        assert "mods/old.jar" in diff.to_delete

    def test_changed_file(self) -> None:
        """sha1 khác → to_download."""
        local = Manifest(MANIFEST_VERSION, "1.21", "fabric", (FileEntry("mods/a.jar", "old", 100),))
        remote = Manifest(MANIFEST_VERSION, "1.21", "fabric", (FileEntry("mods/a.jar", "new", 150),))
        diff = diff_manifest(local, remote)
        assert len(diff.to_download) == 1
        assert diff.to_download[0].sha1 == "new"
        assert diff.to_delete == ()


class TestSerialisation:
    """manifest_to_dict ↔ manifest_from_dict khứ hồi."""

    def test_round_trip(self) -> None:
        entries = (
            FileEntry("mods/a.jar", "abc123", 100),
            FileEntry("config/mod.toml", "def456", 50),
        )
        original = Manifest(MANIFEST_VERSION, "1.21", "fabric", entries)
        serialised = manifest_to_dict(original)
        restored = manifest_from_dict(serialised)
        assert restored.manifest_version == original.manifest_version
        assert restored.game_version == original.game_version
        assert restored.loader_kind == original.loader_kind
        assert len(restored.entries) == len(original.entries)
        for a, b in zip(original.entries, restored.entries):
            assert a.relative_path == b.relative_path
            assert a.sha1 == b.sha1
            assert a.size == b.size

    def test_json_serialisable(self) -> None:
        """Dict phải serialise được bằng json.dumps."""
        manifest = Manifest(MANIFEST_VERSION, "1.21", "vanilla", ())
        text = json.dumps(manifest_to_dict(manifest))
        assert isinstance(text, str)


class TestSafePathsOnly:
    """safe_paths_only lọc đường dẫn nguy hiểm."""

    def test_safe_paths(self, tmp_path: Path) -> None:
        entries = (
            FileEntry("mods/a.jar", "abc", 100),
            FileEntry("config/b.toml", "def", 50),
        )
        result = safe_paths_only(entries, tmp_path)
        assert len(result) == 2

    def test_filters_traversal(self, tmp_path: Path) -> None:
        entries = (
            FileEntry("mods/../../etc/passwd", "bad", 100),
            FileEntry("mods/good.jar", "ok", 50),
        )
        result = safe_paths_only(entries, tmp_path)
        assert len(result) == 1
        assert result[0].relative_path == "mods/good.jar"
