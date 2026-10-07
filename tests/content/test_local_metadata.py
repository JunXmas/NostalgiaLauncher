"""Offline modpack inventory: names, versions, invalidation and bounded archive reads."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from nostalgia.content.installed import list_installed, set_enabled
from nostalgia.content.local_metadata import refresh_metadata


@pytest.mark.parametrize(
    "member,payload",
    [
        ("fabric.mod.json", json.dumps({"id": "sample", "name": "Tên mod", "version": "2.3"})),
        (
            "quilt.mod.json",
            json.dumps(
                {
                    "quilt_loader": {
                        "id": "sample",
                        "version": "2.3",
                        "metadata": {"name": "Tên mod"},
                    }
                }
            ),
        ),
        (
            "META-INF/mods.toml",
            '[[mods]]\nmodId="sample"\ndisplayName="Tên mod"\nversion="${file.jarVersion}"',
        ),
        (
            "META-INF/neoforge.mods.toml",
            '[[mods]]\nmodId="sample"\ndisplayName="Tên mod"\nversion="2.3"',
        ),
    ],
)
def test_offline_metadata_and_disabled_mod_keep_identity(
    tmp_path: Path, member: str, payload: str
) -> None:
    mods = tmp_path / "mods"
    mods.mkdir()
    with zipfile.ZipFile(mods / "random-filename.jar", "w") as archive:
        archive.writestr(member, payload)
        archive.writestr("META-INF/MANIFEST.MF", "Implementation-Version: 2.3\r\n")
    refresh_metadata(mods, list_installed(tmp_path, "mod"))
    installed_content = list_installed(tmp_path, "mod")[0]
    assert (
        installed_content.label,
        installed_content.version_number,
        installed_content.project_id,
    ) == ("Tên mod", "2.3", "")
    set_enabled(tmp_path, "mod", installed_content.file_name, False)
    installed_content = list_installed(tmp_path, "mod")[0]
    assert not installed_content.enabled and installed_content.label == "Tên mod"


def test_metadata_cache_reuses_unchanged_files_and_invalidates_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nostalgia.content import local_metadata

    mods = tmp_path / "mods"
    mods.mkdir()
    path = mods / "manual.jar"

    def write(name: str, version_number: str) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "fabric.mod.json",
                json.dumps({"id": "sample", "name": name, "version": version_number}),
            )

    write("Trước", "1.0")
    refresh_metadata(mods, list_installed(tmp_path, "mod"))
    real_read = local_metadata.read_labels
    monkeypatch.setattr(
        local_metadata, "read_labels", lambda _p: pytest.fail("unchanged JAR rescanned")
    )
    refresh_metadata(mods, list_installed(tmp_path, "mod"))
    assert list_installed(tmp_path, "mod")[0].label == "Trước"
    write("Sau khi thay file", "2.0")
    assert list_installed(tmp_path, "mod")[0].version_number == ""
    monkeypatch.setattr(local_metadata, "read_labels", real_read)
    refresh_metadata(mods, list_installed(tmp_path, "mod"))
    assert list_installed(tmp_path, "mod")[0].label == "Sau khi thay file"


def test_bad_or_oversized_metadata_remains_a_manageable_file(tmp_path: Path) -> None:
    mods = tmp_path / "mods"
    mods.mkdir()
    (mods / "broken.jar").write_bytes(b"not a zip")
    with zipfile.ZipFile(mods / "large.jar", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("fabric.mod.json", b"x" * 262145)
    refresh_metadata(mods, list_installed(tmp_path, "mod"))
    assert [installed_content.label for installed_content in list_installed(tmp_path, "mod")] == [
        "broken.jar",
        "large.jar",
    ]
