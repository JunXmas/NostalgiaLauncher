"""Players can update the same instance, and active Minecraft prevents the action."""

from pathlib import Path
from typing import Any, cast

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QGuiApplication
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.api import Instance, Launcher
from nostalgia.content.builtin_receipt import BuiltinReceipt, save_builtin_receipt
from nostalgia.storage.files import atomic_write_json
from nostalgia.ui.bridge import LauncherBridge
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_manager_updates_existing_pack_and_refreshes_version(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, view, bridge, root_item = preview
    atomic_write_json(launcher.paths.version_json("1.21.11"), {"id": "1.21.11"})
    instance = launcher.create_instance(Instance("industry", "1.21.11", "Ma nha may"))
    registry = launcher.paths.instance_dir(instance.instance_id)
    save_builtin_receipt(registry, BuiltinReceipt("1.0.1", {}))
    calls: list[str] = []

    def update(_self: Launcher, instance_id: str, **_kwargs: Any) -> Instance:
        calls.append(instance_id)
        save_builtin_receipt(registry, BuiltinReceipt("1.0.2", {}))
        return instance

    monkeypatch.setattr(Launcher, "update_builtin_modpack", update)
    bridge.announce_instances_changed()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    manager = find_control(root_item, "modernInstanceManager")
    manager.openFor(cast(Any, bridge).instances[0])
    wait_until(lambda: manager.property("opened"))
    action = find_control(manager, "instanceModpackUpdate")
    assert action.property("clickable")
    press(view, action)
    wait_until(lambda: bool(calls) and not bridge.busy)
    assert calls == ["industry"]
    assert not action.property("clickable")
    assert launcher.list_instances() == (instance,)


def test_update_slot_refuses_while_minecraft_is_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    bridge = LauncherBridge(launcher)
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(Launcher, "update_builtin_modpack", lambda *a, **_k: calls.append(a))
    errors: list[str] = []
    bridge.failed.connect(errors.append)
    bridge._game_running = True
    bridge.updateModpack("industry")
    QGuiApplication.processEvents()
    assert not calls
    assert len(errors) == 1


@pytest.mark.parametrize("instance_name", ["Vanilla", "Fabulously Optimized", "Forgotten Worlds"])
def test_update_button_is_only_visible_for_the_server_pack(
    preview: Preview, instance_name: str
) -> None:
    launcher, _view, bridge, root_item = preview
    version_id = (
        "fabric-loader-0.19.5-1.21.11" if instance_name == "Fabulously Optimized" else "1.21.11"
    )
    atomic_write_json(launcher.paths.version_json(version_id), {"id": version_id, "jar": "1.21.11"})
    launcher.create_instance(Instance("ordinary", version_id, instance_name))
    if instance_name == "Fabulously Optimized":
        from nostalgia.content.pack_origin import save_pack_origin
        from nostalgia.model.pack import PackReference

        save_pack_origin(
            launcher.paths.instance_dir("ordinary"),
            PackReference("modrinth", "1KVo5zza", "fo-version", "0" * 40, instance_name),
            "1.21.11",
            "fabric",
            "0.19.5",
        )
    bridge.announce_instances_changed()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    instance_row = cast(Any, bridge).instances[0]
    assert instance_row["modpackPreset"] == ""
    manager = find_control(root_item, "modernInstanceManager")
    manager.openFor(instance_row)
    wait_until(lambda: manager.property("opened"))
    assert not find_control(manager, "instanceModpackUpdate").property("visible")
