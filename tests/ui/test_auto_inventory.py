"""Automatic recognition in the existing installed UI, without a manual button press."""

from __future__ import annotations

import hashlib
import json
import threading
import zipfile
from pathlib import Path
from typing import Any

import pytest
from test_bridges import wait_until

from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import SODIUM, fabric_target, make_content_launcher, version_document
from nostalgia.api import Launcher
from nostalgia.errors import NetworkError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


def write_mod(path: Path, title: str, version_number: str = "1.0") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "fabric.mod.json",
            json.dumps({"id": "fixture", "name": title, "version": version_number}),
        )


def test_auto_hash_identification_updates_names_icons_and_installed_badge(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    path = target.game_dir / "mods/pack-file.jar"
    write_mod(path, "Tên trong modpack")
    checksum = hashlib.sha1(path.read_bytes()).hexdigest()
    document = version_document(SODIUM, loaders=["fabric"], url=server.url("/cdn/mod.jar"))
    server_state.add("/modrinth/version_files", json.dumps({checksum: document}).encode())
    server_state.add(
        "/modrinth/projects",
        json.dumps(
            [
                {
                    "id": SODIUM,
                    "slug": "sodium",
                    "title": "Sodium",
                    "icon_url": server.url("/icon.png"),
                }
            ]
        ).encode(),
    )
    worker: Any = ContentBridge(launcher, LauncherBridge(launcher))
    worker.selectInstance(target.instance_id)
    worker.refreshInstalled("mod")
    worker.search("mod", "sodium", "relevance")
    wait_until(lambda: bool(worker.installed) and worker.installed[0]["projectId"] == SODIUM)
    wait_until(lambda: bool(worker.results) and worker.results[0]["installed"])
    assert worker.installed[0]["label"] == "Sodium"
    assert worker.installed[0]["iconUrl"] == server.url("/icon.png")
    wait_until(lambda: not worker.identifying)
    for _ in range(3):
        worker.refreshInstalled("mod")
    assert server_state.request_count("/modrinth/version_files") == 1
    wait_for_background()


def test_local_names_arrive_before_network_and_stale_target_never_replaces_new_target(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nostalgia.instance.model import Instance

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    first = fabric_target(launcher)
    launcher.save_instance(Instance("other", launcher.list_instances()[0].version_id))
    second = launcher.describe_content_target("other")
    write_mod(first.game_dir / "mods/first.jar", "Tên A")
    write_mod(second.game_dir / "mods/second.jar", "Tên B")
    release = threading.Event()

    def offline(*_args: object) -> int:
        release.wait(2)
        raise NetworkError("offline fixture")

    monkeypatch.setattr(Launcher, "identify_installed_content", offline)
    worker: Any = ContentBridge(launcher, LauncherBridge(launcher))
    worker.selectInstance(first.instance_id)
    try:
        worker.refreshInstalled("mod")
        wait_until(lambda: worker.installed[0]["label"] == "Tên A")
        assert worker.identifying and not worker.busy
        worker.setEnabled("mod", "first.jar", False)
        assert (first.game_dir / "mods/first.jar.disabled").is_file()
        worker.selectInstance(second.instance_id)
        worker.refreshInstalled("mod")
        release.set()
        wait_until(lambda: bool(worker.installed) and worker.installed[0]["label"] == "Tên B")
        wait_until(lambda: not worker.identifying)
        assert [row["fileName"] for row in worker.installed] == ["second.jar"]
    finally:
        release.set()
        wait_for_background()


def test_directory_changes_refresh_the_list_without_manual_identify(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    write_mod(target.game_dir / "mods/first.jar", "Ban đầu")
    monkeypatch.setattr(Launcher, "identify_installed_content", lambda *_args: 0)
    worker: Any = ContentBridge(launcher, LauncherBridge(launcher))
    worker.selectInstance(target.instance_id)
    worker.refreshInstalled("mod")
    wait_until(lambda: worker.installed[0]["label"] == "Ban đầu")
    (target.game_dir / "mods/first.jar").unlink()
    write_mod(target.game_dir / "mods/new.jar", "Vừa thêm")
    wait_until(lambda: len(worker.installed) == 1 and worker.installed[0]["label"] == "Vừa thêm")
    assert worker.installed[0]["fileName"] == "new.jar"
    wait_for_background()
