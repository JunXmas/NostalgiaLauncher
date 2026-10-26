"""Bật Nos Client từ giao diện: cờ được ghi, jar thật được tải về và chép vào mods/, jar chép
tay cũ bị dọn. Máy chủ GitHub giả trả `releases/latest` như kho JunXmas/nos-client thật."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until

from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import make_content_launcher
from nostalgia.api import Instance
from nostalgia.nos_client import manager
from nostalgia.ui.bridge import LauncherBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_toggle_on_downloads_and_injects_then_off_removes(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    jar = server_state.add("/dl/nos-client-0.2.0.jar", b"PK nos 0.2.0")
    server_state.add(
        "/repos/JunXmas/nos-client/releases/latest",
        json.dumps(
            {
                "tag_name": "v0.2.0",
                "assets": [
                    {
                        "name": "nos-client-0.2.0.jar",
                        "browser_download_url": server.url(jar),
                        "size": 12,
                    }
                ],
            }
        ).encode(),
    )
    monkeypatch.setattr(manager, "GITHUB_API_BASE", server.url(""))
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
