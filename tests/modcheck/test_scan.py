"""JAR thật: phụ thuộc, trùng ID, Forge, mod lồng và metadata không thể đọc."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from mod_fixture import write_fabric
from nostalgia.errors import ContentError
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.predicate import matches
from nostalgia.modcheck.scan import build_scan


def test_fabric_duplicates_missing_breaks_and_game_range(tmp_path: Path) -> None:
    write_fabric(
        tmp_path / "mods/a.jar",
        "alpha",
        depends={"library": ">=2", "minecraft": "~1.21"},
        breaks={"beta": "*"},
    )
    write_fabric(tmp_path / "mods/b.jar", "beta")
    write_fabric(tmp_path / "mods/c.jar", "beta")
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    assert {finding.code for finding in scan.findings} == {
        "missing",
        "version",
        "conflict",
        "duplicate",
    }


def test_forge_prefers_correct_metadata_in_multiloader_jar(tmp_path: Path) -> None:
    path = tmp_path / "mods/a.jar"
    write_fabric(path, "alpha")
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr(
            "META-INF/mods.toml",
            '[[mods]]\nmodId="alpha"\nversion="${file.jarVersion}"\n[[dependencies.alpha]]\nmodId="forge"\nmandatory=true\nversionRange="[47,)"\nside="BOTH"\n',
        )
        archive.writestr("META-INF/MANIFEST.MF", "Implementation-Version: 1.2.3\r\n")
    scan = build_scan(scan_archives(tmp_path, "forge"), "1.20.1", "forge", "47.4.23", 17)
    assert not scan.findings and scan.archives[0].descriptors[0].version_number == "1.2.3"


def test_nested_mod_dependency_is_found_without_extracting(tmp_path: Path) -> None:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("fabric.mod.json", '{"id":"embedded","version":"1.0.0"}')
    write_fabric(
        tmp_path / "mods/a.jar",
        "alpha",
        depends={"embedded": "*"},
        jars=[{"file": "META-INF/jars/embedded.jar"}],
    )
    with zipfile.ZipFile(tmp_path / "mods/a.jar", "a") as archive:
        archive.writestr("META-INF/jars/embedded.jar", payload.getvalue())
    assert not build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17).findings
    assert not (tmp_path / "META-INF").exists()


def test_broken_metadata_and_symlink_never_become_clean(tmp_path: Path) -> None:
    (tmp_path / "mods").mkdir()
    path = tmp_path / "mods/a.jar"
    path.write_bytes(b"invalid")
    assert scan_archives(tmp_path)[0].problem
    path.unlink()
    try:
        path.symlink_to(tmp_path / "outside.jar")
    except OSError:
        pytest.skip("Hệ này không hỗ trợ symlink cho test.")
    with pytest.raises(ContentError):
        scan_archives(tmp_path)


@pytest.mark.parametrize(
    "version_number,predicate,result",
    [
        ("1.20.1", "~1.20.1", True),
        ("1.21", "~1.20.1", False),
        ("47.4.23", "maven:[47,48)", True),
        ("48", "maven:[47,48)", False),
        ("0.92.2+1.20.1", ">=0.90", True),
        ("1.0-beta", "*", True),
        ("1.0-beta", ">=1", None),
        ("1.2.3", ">=1 <2", True),
        ("0.2.1", "^0.2", True),
        ("1.9", "~1", True),
        ("0.9", "^0", True),
        ("0.0.9", "^0.0", True),
        ("0.0.9", "^0.0.1", False),
    ],
)
def test_version_rules(version_number: str, predicate: str, result: bool | None) -> None:
    assert matches(version_number, predicate) is result
