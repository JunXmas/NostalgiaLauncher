"""Modern creation dispatch, visible provider logos and persistent favourite feedback."""

from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview
from test_modern_workspace import prepare_instance

from nostalgia.api import InstallReport, Launcher
from nostalgia.version.meta import VersionMeta
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_new_creator_dispatches_selected_game_loader_and_default_name(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, view, _bridge, root_item = preview
    installed: list[tuple[str, str, str | None]] = []

    def install(
        _launcher: Launcher,
        loader_kind: str,
        game_version: str,
        loader_version: str | None,
        **_kwargs: Any,
    ) -> InstallReport:
        installed.append((loader_kind, game_version, loader_version))
        return InstallReport(
            VersionMeta("1.21.1", "main"), launcher.paths.data_dir / "java", 0, 0, 0
        )

    monkeypatch.setattr(Launcher, "install_loader", install)
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    catalog_bridge = view.rootContext().contextProperty("catalogBridge")
    catalog_bridge._released = [{"versionId": "1.21.1", "major": "1.21"}]
    catalog_bridge._preset_versions = ["1.21.1"]
    catalog_bridge.releasedVersionsChanged.emit()
    catalog_bridge.presetVersionsChanged.emit()
    press(view, find_control(root_item, "createModernInstance"))
    dialog = find_control(root_item, "modernCreateDialog")
    dialog.pickLoader("vanilla")
    select = find_control(root_item, "createGameVersion")
    press(view, select, Qt.Key.Key_Space)
    wait_until(lambda: find_control(root_item, "createGameVersionMenu").property("opened"))
    QTest.keyClick(view, Qt.Key.Key_Return)
    assert dialog.property("gameVersion") == "1.21.1"
    assert dialog.property("canCreate")
    press(view, find_control(root_item, "createInstanceConfirm"))
    wait_until(lambda: bool(launcher.list_instances()) and not catalog_bridge.busy)
    assert installed == [("vanilla", "1.21.1", None)]
    assert launcher.list_instances()[0].display_name == "Vanilla 1.21.1"
    wait_until(lambda: not dialog.property("visible"))


@pytest.mark.parametrize(
    "provider,button_name", [("google", "loginGoogleService"), ("microsoft", "loginMicrosoft")]
)
def test_sign_in_buttons_load_recognizable_provider_marks(
    preview: Preview, provider: str, button_name: str
) -> None:
    _launcher, _view, _bridge, root_item = preview
    button = find_control(root_item, button_name)
    logo = find_control(button, "providerLogo-" + provider)
    mark = logo.parentItem()
    wait_until(lambda: mark.property("ready"))
    assert logo.property("visible")
    assert (
        logo.property("source")
        .toString()
        .endswith("providers/" + ("google.png" if provider == "google" else "microsoft.svg"))
    )


def test_favourite_persists_and_feedback_settles(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    prepare_instance(preview)
    star = find_item(root_item, "instanceFavorite-survival")
    assert star is not None and not star.property("favorite")
    press(view, star)
    wait_until(lambda: launcher.list_instances()[0].favorite)
    star = find_item(root_item, "instanceFavorite-survival")
    assert star is not None
    QTest.qWait(80)
    star = find_item(root_item, "instanceFavorite-survival")
    assert star is not None and star.property("favorite")
    QTest.qWait(600)
    assert star.property("rotation") == 0
    view.rootContext().contextProperty("settingsBridge").setAppearance(100, False, True, True, "vi")
    press(view, star)
    wait_until(lambda: not launcher.list_instances()[0].favorite)
    star = find_item(root_item, "instanceFavorite-survival")
    assert star is not None and star.property("rotation") == 0
