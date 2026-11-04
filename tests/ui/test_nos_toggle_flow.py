"""Bật Nos Client từ giao diện: cờ được ghi, jar thật được tải về và chép vào mods/, jar chép
tay cũ bị dọn. Máy chủ GitHub giả trả danh sách release như kho JunXmas/nos-client thật."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_main_window import Preview
from test_main_window import preview as preview

from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import make_content_launcher
from nos_fixture import build_nos_jar, build_nos_release
from nostalgia.api import Instance, Launcher
from nostalgia.errors import NetworkError
from nostalgia.nos_client import release
from nostalgia.storage.files import atomic_write_json
from nostalgia.ui.bridge import LauncherBridge
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_toggle_on_downloads_and_injects_then_off_removes(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    body = build_nos_jar(mod_version="0.2.0")
    jar = server_state.add("/dl/nos-client-0.2.0.jar", body)
    server_state.add(
        "/repos/JunXmas/nos-client/releases",
        json.dumps([build_nos_release("nos-client-0.2.0.jar", server.url(jar), body)]).encode(),
    )
    monkeypatch.setattr(release, "GITHUB_API_BASE", server.url(""))
    launcher.create_instance(Instance("opt", "fabric-loader-0.19.3-1.21.11"))
    mods = launcher.paths.instance_dir("opt") / "mods"
    mods.mkdir(parents=True)
    (mods / "nosclient-0.1.0.jar").write_bytes(b"chep tay")
    bridge = LauncherBridge(launcher)
    row = next(i for i in bridge.instances if i["instanceId"] == "opt")
    assert row["nosClientSupported"] is True and row["nosClientEnabled"] is False

    bridge.toggleNosClient("opt", True)
    wait_until(lambda: not bridge.busy)
    assert next(i for i in launcher.list_instances() if i.instance_id == "opt").nos_client_enabled
    assert sorted(p.name for p in mods.iterdir()) == ["nos-client-0.2.0.jar"]

    bridge.toggleNosClient("opt", False)
    wait_until(lambda: not bridge.busy)
    assert not list(mods.iterdir())


def test_failed_enable_does_not_save_enabled_and_can_retry(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    endpoint = server_state.add("/repos/JunXmas/nos-client/releases", b"[]")
    monkeypatch.setattr(release, "GITHUB_API_BASE", server.url(""))
    launcher.create_instance(Instance("opt", "fabric-loader-0.19.3-1.21.11"))
    bridge = LauncherBridge(launcher)
    errors: list[str] = []
    bridge.failed.connect(errors.append)
    bridge.toggleNosClient("opt", True)
    wait_until(lambda: not bridge.busy)
    assert errors and "Nos Client" in errors[-1]
    assert not launcher.list_instances()[0].nos_client_enabled
    assert not bridge.instances[0]["nosClientEnabled"]
    body = build_nos_jar()
    jar = server_state.add("/nos-client-0.4.2.jar", body)
    server_state.routes[endpoint].body = json.dumps(
        [
            build_nos_release("nos-client-0.4.2.jar", server.url(jar), body),
        ]
    ).encode()
    bridge.toggleNosClient("opt", True)
    wait_until(lambda: not bridge.busy)
    assert launcher.list_instances()[0].nos_client_enabled
    assert bridge.instances[0]["nosClientEnabled"]
    assert (launcher.paths.instance_dir("opt") / "mods/nos-client-0.4.2.jar").read_bytes() == body


def test_manager_toggle_keeps_binding_after_failure_and_success(
    preview: Preview,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    launcher, view, bridge, root_item = preview
    fabric = "fabric-loader-0.19.3-1.21.11"
    atomic_write_json(launcher.paths.version_json("1.21.11"), {"id": "1.21.11", "mainClass": "x"})
    atomic_write_json(
        launcher.paths.version_json(fabric), {"id": fabric, "inheritsFrom": "1.21.11"}
    )
    launcher.create_instance(Instance("nos", fabric, "Nos Update Test"))
    bridge.announce_instances_changed()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    manager = find_control(root_item, "modernInstanceManager")
    manager.openFor(next(row for row in bridge.instances if row["instanceId"] == "nos"))
    wait_until(lambda: manager.property("opened"))
    toggle = find_control(root_item, "instanceNosClientToggle")
    failures: list[str] = []
    bridge.failed.connect(failures.append)

    def fail(_self: Launcher, _instance: Instance) -> None:
        raise NetworkError("Nos Client download unavailable")

    monkeypatch.setattr(Launcher, "prepare_nos_client", fail)
    press(view, toggle, Qt.Key.Key_Space)
    wait_until(lambda: bool(failures) and not bridge.busy)
    assert not toggle.property("checked")
    assert not launcher.list_instances()[0].nos_client_enabled
    assert view.grabWindow().save(str(tmp_path / "nos-update-failed.png"))

    def ready(_self: Launcher, _instance: Instance) -> None:
        pass

    monkeypatch.setattr(Launcher, "prepare_nos_client", ready)
    assert toggle.property("enabled")
    press(view, toggle, Qt.Key.Key_Space)
    wait_until(lambda: not bridge.busy and bool(toggle.property("checked")))
    assert launcher.list_instances()[0].nos_client_enabled
    QTest.qWait(300)
    assert view.grabWindow().save(str(tmp_path / "nos-update-enabled.png"))
