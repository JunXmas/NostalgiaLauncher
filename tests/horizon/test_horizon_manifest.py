"""Bảo đảm Horizon dùng manifest Mojang gốc đã ghim, không sửa cache Java."""

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from nostalgia.errors import InstanceError, IntegrityError
from nostalgia.horizon.model import HorizonBuild
from nostalgia.horizon.process import HorizonTaskReport
from nostalgia.horizon.resource import prepare_resources, sync_horizon_manifest
from nostalgia.storage.paths import DataPaths


@pytest.fixture
def build_with_manifest(tmp_path: Path) -> tuple[HorizonBuild, bytes]:
    build_dir = tmp_path / "horizon" / "builds" / ("a" * 64) / "bundle"
    build = HorizonBuild("a" * 64, build_dir, "26.3", 25)
    build.build_dir.mkdir(parents=True)
    payload = b'{"id":"26.3","downloads":{"server":{"sha1":"abc"}}}'
    sha1 = hashlib.sha1(payload).hexdigest()
    (build.build_dir / "research-lock.json").write_text(
        json.dumps({"minecraft": {"version": "26.3", "manifest_sha1": sha1}}),
        encoding="utf-8",
    )
    return build, payload


def test_manifest_is_pinned_and_isolated_from_java_cache(
    tmp_path: Path, build_with_manifest: tuple[HorizonBuild, bytes]
) -> None:
    build, payload = build_with_manifest
    paths = DataPaths.for_root(tmp_path)
    java_version = paths.version_json("26.3")
    java_version.parent.mkdir(parents=True)
    java_version.write_bytes(b"unknown but usable Java manifest")
    client = Mock()
    client.fetch_bytes.return_value = payload
    actual = sync_horizon_manifest(client, build)

    assert actual == build.build_dir.parent / "minecraft" / "26.3" / "manifest.json"
    assert actual.read_bytes() == payload
    assert java_version.read_bytes() == b"unknown but usable Java manifest"
    pinned_sha1 = hashlib.sha1(payload).hexdigest()
    client.fetch_bytes.assert_called_once_with(
        f"https://piston-meta.mojang.com/v1/packages/{pinned_sha1}/26.3.json",
        max_bytes=1024 * 1024,
        cancel_token=None,
    )

    client.fetch_bytes.reset_mock()
    assert sync_horizon_manifest(client, build) == actual
    client.fetch_bytes.assert_not_called()


def test_tampered_horizon_manifest_is_repaired(
    build_with_manifest: tuple[HorizonBuild, bytes]
) -> None:
    build, payload = build_with_manifest
    client = Mock()
    client.fetch_bytes.return_value = payload
    destination = sync_horizon_manifest(client, build)
    destination.write_bytes(b"modified-by-foreign-launcher")
    assert sync_horizon_manifest(client, build) == destination
    assert destination.read_bytes() == payload
    assert client.fetch_bytes.call_count == 2


def test_bad_download_does_not_overwrite_existing_manifest(
    build_with_manifest: tuple[HorizonBuild, bytes]
) -> None:
    build, _payload = build_with_manifest
    destination = build.build_dir.parent / "minecraft" / "26.3" / "manifest.json"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old")
    client = Mock()
    client.fetch_bytes.return_value = b"tampered"
    with pytest.raises(IntegrityError, match="SHA-1 mismatch"):
        sync_horizon_manifest(client, build)
    assert destination.read_bytes() == b"old"


def test_invalid_horizon_research_lock_fails_closed(
    build_with_manifest: tuple[HorizonBuild, bytes]
) -> None:
    build, _payload = build_with_manifest
    (build.build_dir / "research-lock.json").write_text(
        '{"minecraft":{"version":"26.3","manifest_sha1":"bad"}}', encoding="utf-8"
    )
    client = Mock()
    with pytest.raises(InstanceError, match="pinned"):
        sync_horizon_manifest(client, build)
    client.fetch_bytes.assert_not_called()


def test_prepare_passes_pinned_manifest_to_native_binary(
    tmp_path: Path,
    build_with_manifest: tuple[HorizonBuild, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build, _payload = build_with_manifest
    paths = DataPaths.for_root(tmp_path)
    version_json = build.build_dir.parent / "minecraft" / "26.3" / "manifest.json"
    commands = []

    def fake_task(command, **_kwargs):
        commands.append(command)
        return HorizonTaskReport(0, ())

    monkeypatch.setattr("nostalgia.horizon.resource.run_horizon_task", fake_task)
    monkeypatch.setattr("nostalgia.horizon.resource.check_resources", lambda *_args: True)
    prepare_resources(
        paths,
        build,
        tmp_path / "java" / "bin" / "java",
        tmp_path / "server.jar",
        version_json=version_json,
    )
    argv = commands[0].argv
    assert argv[argv.index("--version-json") + 1] == str(version_json)
    assert argv[argv.index("--version-json") + 1] != str(paths.version_json("26.3"))
