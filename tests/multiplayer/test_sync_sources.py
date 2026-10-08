"""JAR reconnu par hash téléchargé à la source; une modification privée garde ses octets."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.content.installed import LedgerEntry, save_ledger
from nostalgia.model.pack import PackReference
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ignore_progress
from test_api import make_launcher


class PrivateGateway:
    def __init__(self, payload: bytes) -> None:
        self.payload, self.downloaded = payload, False

    def resolve(self, _room_code: str) -> SyncManifest | None:
        return None

    def publish(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("test transport only downloads")

    def download(self, _room_code: str, _sync_file: SyncFile) -> bytes:
        self.downloaded = True
        return self.payload


@pytest.mark.parametrize("modified", [False, True])
def test_public_hash_and_stale_source_both_verify_exact_host_bytes(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    modified: bool,
) -> None:
    public = b"public jar"
    private = b"custom private jar" if modified else public
    public_sha1 = hashlib.sha1(public).hexdigest()
    release = {
        "id": "r1",
        "project_id": "sodium",
        "version_number": "1",
        "version_type": "release",
        "game_versions": ["1.20.1"],
        "loaders": ["fabric"],
        "date_published": "",
        "files": [
            {
                "url": server.url("/public.jar"),
                "filename": "sodium.jar",
                "primary": True,
                "size": len(public),
                "hashes": {"sha1": public_sha1},
            }
        ],
        "dependencies": [],
    }
    server_state.add("/public.jar", public)
    server_state.add("/modrinth/project/sodium/version", json.dumps([release]).encode())
    server_state.add("/modrinth/version_files", json.dumps({public_sha1: release}).encode())
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, modrinth_api=server.url("/modrinth"))
    )
    sync_file = SyncFile(
        "mods/sodium.jar",
        hashlib.sha256(private).hexdigest(),
        len(private),
        source=PackReference("modrinth", "sodium", "r1") if modified else None,
        sha1=hashlib.sha1(private).hexdigest(),
    )
    manifest = SyncManifest("Custom", "1.20.1", "fabric", "0.16.9", (sync_file,))
    gateway = PrivateGateway(private)
    stage = tmp_path / "guest"
    launcher.sync_room_files(
        gateway, "fixture", manifest, stage, cancel_token=CancelToken(), on_progress=ignore_progress
    )
    assert (stage / "mods/sodium.jar").read_bytes() == private
    assert gateway.downloaded == modified
    assert server_state.request_count("/public.jar") == 1
    assert server_state.request_count("/modrinth/project/sodium/version") == 1
    assert server_state.request_count("/modrinth/version_files") == (0 if modified else 1)


def test_invalid_local_ledger_is_not_exported_as_arbitrary_download_url(tmp_path: Path) -> None:
    from nostalgia.api import Launcher
    from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot

    launcher = Launcher.for_data_dir(tmp_path)
    source = tmp_path / "host"
    (source / "mods").mkdir(parents=True)
    (source / "mods/private.jar").write_bytes(b"private")
    save_ledger(
        source / "mods",
        {
            "https://attacker.invalid": LedgerEntry(
                "https://attacker.invalid", "Private", "r1", "1", "private.jar"
            )
        },
    )
    snapshot = capture_sync_snapshot(
        source,
        tmp_path / "snapshot",
        name="A",
        game_version="1.20.1",
        loader_kind="vanilla",
        loader_version="",
        cancel_token=CancelToken(),
    )
    described = launcher.describe_sync_snapshot(source, snapshot)
    assert described.manifest.files[0].source is None
