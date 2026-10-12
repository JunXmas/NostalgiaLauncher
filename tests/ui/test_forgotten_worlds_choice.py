"""Chọn gói server không cần chọn loader, và bản không tương thích phải bị chặn."""

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from test_bridges import wait_until
from test_create_choices import open_create_dialog

from nostalgia.api import Instance, Launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import CatalogBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_server_pack_is_available_without_a_loader_step(tmp_path: Path) -> None:
    dialog = open_create_dialog(tmp_path)
    assert dialog.findChild(QObject, "forgottenWorldsCard") is not None
    dialog.setProperty("loaderKind", "forgotten-worlds")
    dialog.setProperty("gameVersion", "1.21.11")
    QGuiApplication.processEvents()
    assert dialog.property("isPreset") is True
    assert dialog.property("needsLoaderStep") is False
    assert dialog.property("canCreate") is True
    dialog.setProperty("gameVersion", "1.21.1")
    QGuiApplication.processEvents()
    assert dialog.property("canCreate") is False
    assert dialog.property("gameVersion") == "1.21.1"


def test_catalog_routes_server_pack_and_keeps_requested_ram(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    calls: list[str] = []

    def install_preset(
        self: Launcher, preset: str, instance_id: str, display_name: str, **kwargs: object
    ) -> Instance:
        calls.append(preset)
        instance = Instance(
            instance_id=instance_id,
            version_id="fabric-loader-0.19.5-1.21.11",
            display_name=display_name,
            game_dir_override=str(kwargs["game_dir_override"]),
        )
        return self.create_instance(instance)

    monkeypatch.setattr(Launcher, "install_preset", install_preset)
    main = LauncherBridge(launcher)
    catalog_bridge = CatalogBridge(launcher, main)
    created: list[str] = []
    catalog_bridge.created.connect(created.append)
    catalog_bridge.createInstance("Forgotten Worlds", "1.21.11", "forgotten-worlds", "", 4096, "")
    wait_until(lambda: bool(created))
    assert calls == ["forgotten-worlds"]
    assert launcher.list_instances()[0].max_heap_megabytes == 4096
