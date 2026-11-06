"""Horizon xuất hiện trong tạo bản chơi, giữ native riêng và không cài loader Java."""

from pathlib import Path
from typing import Any

import pytest
from modern_window import go
from PySide6.QtCore import QPointF
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_main_window import Preview
from test_main_window import preview as preview

from nostalgia.api import Instance, Launcher
from nostalgia.horizon.model import HorizonBuild
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def horizon_view(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, preview: Preview
) -> tuple[Preview, list[Instance]]:
    prepared: list[Instance] = []
    build = HorizonBuild("a" * 64, tmp_path / "bundle", "26.3", 25)
    monkeypatch.setattr(Launcher, "list_released_versions", lambda *_a, **_k: ())
    monkeypatch.setattr(Launcher, "list_preset_game_versions", lambda *_a, **_k: ())
    monkeypatch.setattr(Launcher, "install_horizon", lambda *_a, **_k: build)
    monkeypatch.setattr(
        Launcher,
        "prepare_horizon_instance",
        lambda _self, instance, **_k: prepared.append(instance),
    )

    def deny_loader(*_args: Any, **_options: Any) -> None:
        pytest.fail("Horizon must not install a Java mod loader")

    monkeypatch.setattr(Launcher, "install_loader", deny_loader)
    return preview, prepared


@pytest.mark.parametrize(("language", "scale"), [("en", 100), ("vi", 150)])
def test_horizon_choice_creates_a_separate_native_instance(
    horizon_view: tuple[Preview, list[Instance]], tmp_path: Path, language: str, scale: int
) -> None:
    (launcher, view, bridge, root_item), prepared = horizon_view
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, True, True, False, language
    )
    root_item.setProperty("sessionSkipped", True)
    go(root_item, 1, "minimalInstances")
    dialog = find_control(root_item, "modernCreateDialog")
    dialog.openDialog()
    catalog_bridge = view.rootContext().contextProperty("catalogBridge")
    wait_until(lambda: not catalog_bridge.busy)
    dialog.pickLoader("horizon")
    assert dialog.property("gameVersion") == "26.3"
    assert dialog.property("isHorizon")
    assert not dialog.property("needsLoaderStep")
    assert not find_control(root_item, "createGameVersion").isEnabled()
    setup = find_control(root_item, "createSetupSection")
    scroll = find_control(root_item, "createFormScroll")
    position = setup.mapToItem(scroll, QPointF()).y() + scroll.property("contentY")
    scroll.scrollBy(position - scroll.property("contentY"), True)
    QTest.qWait(150)
    assert view.grabWindow().save(str(tmp_path / f"horizon-create-{language}-{scale}.png"))
    catalog_bridge.createInstance("Horizon QA", "26.3", "horizon", "", 8192, "")
    wait_until(lambda: bool(launcher.list_instances()) and not catalog_bridge.busy)
    assert len(prepared) == 1
    instance = launcher.list_instances()[0]
    assert instance.runtime_kind == "horizon"
    assert instance.version_id == "horizon-26.3"
    assert instance.horizon_build_id == "a" * 64
    assert instance.max_heap_megabytes is None
    assert not launcher.nos_client_supported(instance)
    assert not dialog.property("opened")
    bridge.announce_instances_changed()
    row = next(
        row for row in bridge.property("instances") if row["instanceId"] == instance.instance_id
    )
    assert row["gameVersion"] == "26.3" and not row["nosClientSupported"]
