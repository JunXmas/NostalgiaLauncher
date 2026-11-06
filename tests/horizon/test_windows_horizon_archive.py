"""Giải nén, công bố và dọn build dài trên Windows thật, cả khi LongPathsEnabled=0."""

import base64
import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from nostalgia.errors import InstanceError, IntegrityError
from nostalgia.horizon.archive import extract_horizon_bundle
from nostalgia.horizon.model import HorizonBuild
from nostalgia.horizon.release import RELEASE_URL, sync_horizon_build
from nostalgia.net.http import HttpClient
from nostalgia.storage.paths import DataPaths
from nostalgia.storage.windows_path import extended_windows_path
from nostalgia.system.platform_info import Platform

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="requires real Windows file APIs")

DEEP_MEMBER = (
    "tools/fixtures/biome_datapacks/horizon_biome_test/data/"
    "horizon_test/worldgen/biome/ember_fields.json"
)


def normal_path(path: Path) -> Path:
    """pytest có thể cấp temp path đã mở rộng; ca hồi quy cần đường dẫn thường như người dùng."""
    spelling = str(path)
    if spelling.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + spelling[8:])
    return Path(spelling.removeprefix("\\\\?\\"))


def write_bundle(archive_path: Path, *, complete: bool = True) -> None:
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("horizon-windows-x64/" + DEEP_MEMBER, b'{"test":true}')
        if complete:
            archive.writestr("horizon-windows-x64/research-lock.json", "{}")
            archive.writestr("horizon-windows-x64/exporters/manifest.json", "{}")


def test_windows_extracts_past_max_path_and_cleans_up(tmp_path: Path) -> None:
    tmp_path = normal_path(tmp_path)
    archive_path = tmp_path / "bundle.zip"
    write_bundle(archive_path)
    staging_dir = tmp_path / ("stage-" + "p" * 72)
    destination = staging_dir / "horizon-windows-x64" / DEEP_MEMBER
    assert len(str(destination)) > 260
    try:
        extended_windows_path(destination.parent).mkdir(parents=True)
        if os.environ.get("NOSTALGIA_TEST_WINDOWS_MAX_PATH") == "1":
            with pytest.raises(OSError):
                destination.write_bytes(b"must fail without extended prefix")
        build_dir = extract_horizon_bundle(archive_path, staging_dir)
        assert (build_dir / DEEP_MEMBER).read_bytes() == b'{"test":true}'
        assert (build_dir / "exporters/manifest.json").is_file()
    finally:
        shutil.rmtree(extended_windows_path(staging_dir), ignore_errors=True)
    assert not staging_dir.exists()


@pytest.mark.parametrize("failure", ["none", "archive", "api"])
def test_windows_install_publish_or_failure_removes_long_staging_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    tmp_path = normal_path(tmp_path)
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    archive_path = tmp_path / "bundle.zip"
    write_bundle(archive_path, complete=failure != "archive")
    blob = archive_path.read_bytes()
    build_id = hashlib.sha256(blob).hexdigest()
    build_dir = paths.data_dir / "horizon/builds" / build_id / "bundle"
    assert len(str(build_dir / DEEP_MEMBER)) > 260
    asset_name = "horizon-windows-x64.zip"
    checksums = f"{build_id}  {asset_name}\n".encode()
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setattr(
        "nostalgia.horizon.release.RELEASE_KEY", base64.b64encode(public_key).decode()
    )
    signature = base64.b64encode(private_key.sign(b"horizon release nightly\n" + checksums))
    transport = Mock(spec=HttpClient)
    transport.fetch_bytes.side_effect = lambda url, **_k: {
        f"{RELEASE_URL}/SHA256SUMS": checksums,
        f"{RELEASE_URL}/SHA256SUMS.sig": signature,
    }[url]

    def stream(_url: str, write: Any, **_options: Any) -> int:
        write(blob)
        return len(blob)

    transport.stream.side_effect = stream

    def load(*_args: Any) -> HorizonBuild:
        if failure == "api":
            raise InstanceError("Invalid test API")
        return HorizonBuild(build_id, build_dir, "26.3", 25, ".exe")

    monkeypatch.setattr("nostalgia.horizon.release.load_build", load)
    try:
        if failure == "none":
            build = sync_horizon_build(transport, paths, Platform("windows", "x64", ""))
            assert build.build_dir == build_dir
            assert not str(build.build_dir).startswith("\\\\?\\")
            assert extended_windows_path(build_dir / DEEP_MEMBER).read_bytes() == b'{"test":true}'
            assert extended_windows_path(build_dir.parent / "receipt.json").is_file()
        else:
            with pytest.raises(IntegrityError if failure == "archive" else InstanceError):
                sync_horizon_build(transport, paths, Platform("windows", "x64", ""))
            assert not extended_windows_path(build_dir).exists()
        assert not tuple(extended_windows_path(build_dir.parent).glob("stage-*"))
    finally:
        shutil.rmtree(extended_windows_path(paths.data_dir), ignore_errors=True)
