"""Không đưa metadata cache bị viết lại cho engine ghim hash theo byte."""

import hashlib
import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from nostalgia.errors import Cancelled, IntegrityError, NetworkError
from nostalgia.horizon.input import sync_horizon_inputs, write_cached_input
from nostalgia.horizon.model import HorizonBuild
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.net.retry import RetryPolicy
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import atomic_write_json
from nostalgia.storage.paths import DataPaths


@dataclass(frozen=True, slots=True)
class InputFixture:
    paths: DataPaths
    build: HorizonBuild
    transport: Any
    version_bytes: bytes
    index_bytes: bytes
    asset_bytes: bytes


@pytest.fixture
def pinned_inputs(tmp_path: Path) -> InputFixture:
    paths = DataPaths(tmp_path / "data", tmp_path / "config")
    build = HorizonBuild("a" * 64, tmp_path / "build" / "bundle", "26.3", 25)
    asset_bytes = b"verified asset"
    asset_hash = hashlib.sha1(asset_bytes).hexdigest()
    index_bytes = json.dumps(
        {"objects": {"test/asset": {"hash": asset_hash, "size": len(asset_bytes)}}}
    ).encode()
    client_bytes, server_bytes = b"verified client", b"verified server"
    client_hash, server_hash = (
        hashlib.sha1(client_bytes).hexdigest(),
        hashlib.sha1(server_bytes).hexdigest(),
    )
    version_bytes = json.dumps(
        {
            "id": "26.3",
            "mainClass": "net.minecraft.client.main.Main",
            "downloads": {
                "client": {
                    "url": "https://mojang.test/client.jar",
                    "sha1": client_hash,
                    "size": len(client_bytes),
                },
                "server": {
                    "url": "https://mojang.test/server.jar",
                    "sha1": server_hash,
                    "size": len(server_bytes),
                },
            },
            "assetIndex": {
                "id": "34",
                "url": "https://mojang.test/34.json",
                "sha1": hashlib.sha1(index_bytes).hexdigest(),
                "size": len(index_bytes),
            },
        }
    ).encode()
    sha1 = hashlib.sha1(version_bytes).hexdigest()
    atomic_write_json(
        build.build_dir / "research-lock.json",
        {
            "minecraft": {
                "version": "26.3",
                "java_major": 25,
                "manifest_sha1": sha1,
                "client_sha1": client_hash,
                "server_sha1": server_hash,
            }
        },
    )
    transport = Mock(spec=HttpClient)
    payloads = {
        f"https://piston-meta.mojang.com/v1/packages/{sha1}/26.3.json": version_bytes,
        "https://mojang.test/34.json": index_bytes,
        "https://mojang.test/client.jar": client_bytes,
        "https://mojang.test/server.jar": server_bytes,
        f"https://resources.download.minecraft.net/{asset_hash[:2]}/{asset_hash}": asset_bytes,
    }

    def stream(url: str, write: Any, **_options: Any) -> int:
        payload = payloads[url]
        write(payload)
        return len(payload)

    transport.stream.side_effect = stream
    return InputFixture(paths, build, transport, version_bytes, index_bytes, asset_bytes)


def test_rewritten_shared_metadata_is_left_intact_and_pinned_bytes_are_isolated(
    pinned_inputs: InputFixture,
) -> None:
    fixture = pinned_inputs
    version_path = fixture.paths.version_json("26.3")
    atomic_write_json(version_path, json.loads(fixture.version_bytes))
    index_path = fixture.paths.asset_index_json("34")
    atomic_write_json(index_path, {"objects": {}, "republished": True})
    before_version, before_index = version_path.read_bytes(), index_path.read_bytes()
    inputs = sync_horizon_inputs(fixture.transport, fixture.paths, fixture.build)
    assert inputs.paths.version_json("26.3").read_bytes() == fixture.version_bytes
    assert inputs.paths.asset_index_json("34").read_bytes() == fixture.index_bytes
    assert version_path.read_bytes() == before_version
    assert index_path.read_bytes() == before_index
    assert inputs.paths.assets_dir != fixture.paths.assets_dir
    assert fixture.transport.stream.call_count == 2
    fixture.transport.reset_mock()
    assert sync_horizon_inputs(fixture.transport, fixture.paths, fixture.build) == inputs
    fixture.transport.stream.assert_not_called()


def test_corrupt_same_size_private_cache_is_checked_by_hash(pinned_inputs: InputFixture) -> None:
    fixture = pinned_inputs
    inputs = sync_horizon_inputs(fixture.transport, fixture.paths, fixture.build)
    version_path = inputs.paths.version_json("26.3")
    version_path.write_bytes(fixture.version_bytes.replace(b"26.3", b"26.4"))
    index_path = inputs.paths.asset_index_json("34")
    index_path.write_bytes(b"x" * len(fixture.index_bytes))
    fixture.transport.reset_mock()
    sync_horizon_inputs(fixture.transport, fixture.paths, fixture.build)
    assert fixture.transport.stream.call_count == 2
    assert version_path.read_bytes() == fixture.version_bytes
    assert index_path.read_bytes() == fixture.index_bytes


def test_bad_download_hash_does_not_publish_manifest(
    pinned_inputs: InputFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = pinned_inputs
    monkeypatch.setattr(
        "nostalgia.horizon.input.download_one",
        partial(download_one, retry_policy=RetryPolicy(attempts=1)),
    )

    def corrupt(_url: str, write: Any, **_options: Any) -> int:
        write(b"wrong manifest")
        return len(b"wrong manifest")

    fixture.transport.stream.side_effect = corrupt
    with pytest.raises(NetworkError, match="sha1") as failure:
        sync_horizon_inputs(fixture.transport, fixture.paths, fixture.build)
    assert isinstance(failure.value.__cause__, IntegrityError)
    assert not (fixture.build.build_dir.parent / "inputs/versions/26.3/26.3.json").exists()


@pytest.mark.parametrize("link_object", [False, True])
def test_verified_cache_reuse_and_copy_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_object: bool
) -> None:
    source = tmp_path / "shared"
    source.write_bytes(b"correct")
    target = tmp_path / "private" / "object"
    task = DownloadTask("https://mojang.test/object", target, hashlib.sha1(b"correct").hexdigest())
    monkeypatch.setattr("nostalgia.horizon.input.os.link", Mock(side_effect=OSError("no links")))
    write_cached_input(task, source, link_object=link_object)
    assert target.read_bytes() == b"correct" and source.read_bytes() == b"correct"
    source.write_bytes(b"changed")
    assert target.read_bytes() == b"correct"


def test_cancelled_input_does_not_download(pinned_inputs: InputFixture) -> None:
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        sync_horizon_inputs(
            pinned_inputs.transport, pinned_inputs.paths, pinned_inputs.build, cancel_token
        )
    pinned_inputs.transport.stream.assert_not_called()
