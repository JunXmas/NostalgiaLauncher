"""Chạy chuỗi chuẩn bị bằng transport giả, giữ cache Java và chỉ dùng đầu vào đã ghim."""

import hashlib
from pathlib import Path
from typing import Any

import pytest
from test_input import InputFixture
from test_input import pinned_inputs as pinned_inputs

from nostalgia.errors import IntegrityError
from nostalgia.horizon.command import HorizonCommand
from nostalgia.horizon.input import sync_horizon_inputs
from nostalgia.horizon.preparation import sync_horizon_preparation
from nostalgia.horizon.process import HorizonTaskReport
from nostalgia.horizon.resource import prepare_resources
from nostalgia.java.mojang_jre import InstalledRuntime
from nostalgia.storage.files import atomic_write_json
from nostalgia.system.platform_info import Platform


def test_preparation_uses_private_metadata_without_rewriting_java_cache(
    pinned_inputs: InputFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = pinned_inputs
    atomic_write_json(fixture.paths.version_json("26.3"), {"id": "26.3", "rewritten": True})
    original = fixture.paths.version_json("26.3").read_bytes()
    java_binary = tmp_path / "java" / "bin" / "java"
    monkeypatch.setattr(
        "nostalgia.horizon.preparation.ensure_java_runtime",
        lambda *_a, **_k: InstalledRuntime(java_binary, "java-runtime-delta", "linux", "25"),
    )
    prepared = sync_horizon_preparation(
        fixture.transport, fixture.paths, fixture.build, Platform("linux", "x64", "")
    )
    assert prepared.input_paths.version_json("26.3").read_bytes() == fixture.version_bytes
    assert fixture.paths.version_json("26.3").read_bytes() == original
    asset_hash = hashlib.sha1(fixture.asset_bytes).hexdigest()
    assert prepared.input_paths.asset_object(asset_hash).read_bytes() == fixture.asset_bytes
    assert prepared.server_jar.read_bytes() == b"verified server"
    commands: list[HorizonCommand] = []

    def capture(command: HorizonCommand, **_options: Any) -> HorizonTaskReport:
        commands.append(command)
        return HorizonTaskReport(0, ())

    monkeypatch.setattr("nostalgia.horizon.resource.run_horizon_task", capture)
    monkeypatch.setattr("nostalgia.horizon.resource.check_resources", lambda *_a: True)
    prepare_resources(
        fixture.paths,
        fixture.build,
        prepared.java_binary,
        prepared.server_jar,
        input_paths=prepared.input_paths,
    )
    argv = commands[0].argv
    assert argv[argv.index("--version-json") + 1] == str(prepared.input_paths.version_json("26.3"))
    assert argv[argv.index("--assets-dir") + 1] == str(prepared.input_paths.assets_dir)
    assert argv[argv.index("--libraries-dir") + 1] == str(fixture.paths.libraries_dir)


@pytest.mark.parametrize("field", ["version", "java_major", "manifest_sha1", "client_sha1"])
def test_incomplete_research_lock_fails_before_network(
    pinned_inputs: InputFixture, field: str
) -> None:
    import json

    lock_path = pinned_inputs.build.build_dir / "research-lock.json"
    document = json.loads(lock_path.read_text())
    document["minecraft"].pop(field)
    atomic_write_json(lock_path, document)
    with pytest.raises(IntegrityError):
        sync_horizon_inputs(pinned_inputs.transport, pinned_inputs.paths, pinned_inputs.build)
    pinned_inputs.transport.stream.assert_not_called()
