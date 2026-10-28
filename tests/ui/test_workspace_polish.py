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


def test_modern_creator_offers_legacy_fabric_only_for_old_versions(preview: Preview) -> None:
    """1.2.0rc40 chỉ thêm Legacy Fabric vào hộp tạo CŨ; giao diện người dùng thật đang dùng là
    hộp hiện đại, nên mục này không hiện ra (chủ dự án báo 26/10/2026)."""
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    catalog_bridge = view.rootContext().contextProperty("catalogBridge")
    catalog_bridge._released = [
        {"versionId": v, "major": v.rsplit(".", 1)[0]} for v in ("26.1.2", "1.21.1", "1.12.2")
    ]
    catalog_bridge.releasedVersionsChanged.emit()
    press(view, find_control(root_item, "createModernInstance"))
    dialog = find_control(root_item, "modernCreateDialog")
    wait_until(lambda: dialog.property("opened"))
    labels = [choice["label"] for choice in dialog.property("loaderChoices").toVariant()]
    assert "Legacy Fabric" in labels
    find_control(root_item, "createLoader-legacy_fabric")  # nút thật được dựng
    dialog.pickLoader("legacy_fabric")
    for too_new in ("1.21.1", "26.1.2"):
        dialog.setProperty("gameVersion", too_new)
        assert dialog.property("legacyTooNew") is True
        assert "Legacy Fabric" in dialog.property("blockedReason")
    dialog.setProperty("gameVersion", "1.12.2")
    assert dialog.property("legacyTooNew") is False


def test_nos_chip_on_instance_tile_toggles_nos_client(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Công tắc Nos phải nằm ngay trên thẻ bản chơi: trước chỉ có trong Quản lý → Tổng quan và
    chủ dự án thấy người chơi không tìm ra (27/10/2026). Bản chơi vanilla thì không hiện."""
    from nostalgia.instance.model import Instance
    from nostalgia.model.json_value import JsonValue
    from nostalgia.storage.files import atomic_write_json

    launcher, view, bridge, root_item = preview
    fabric_id = "fabric-loader-0.19.3-1.21.11"
    for version_id, parent in (("1.21.11", {}), (fabric_id, {"inheritsFrom": "1.21.11"})):
        document: dict[str, JsonValue] = {"id": version_id, "mainClass": "x", "type": "release"}
        document.update(parent)
        atomic_write_json(launcher.paths.version_json(version_id), document)
    launcher.save_instance(Instance("fab", fabric_id, display_name="Fab"))
    launcher.save_instance(Instance("van", "1.21.11", display_name="Van"))
    monkeypatch.setattr(Launcher, "prepare_nos_client", lambda *_args: None)  # không chạm mạng
    bridge.announce_instances_changed()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)

    # Cùng tên có thể có nhiều bản (thẻ trang chủ đang ẩn, thẻ Bản chơi đang hiện): lấy bản hiện.
    def visible_chip(instance_id: str) -> Any:
        return visible_item("nosChip-" + instance_id)

    def visible_item(name: str) -> Any:
        pending = [root_item]  # duyệt cây hình (delegate không nằm trong cây QObject)
        while pending:
            node = pending.pop()
            if node.objectName() == name and node.isVisible():
                return node
            pending.extend(node.childItems())
        return None

    wait_until(lambda: visible_chip("fab") is not None)
    assert visible_chip("van") is None
    # Thẻ lưới hẹp: chip từng đè lên nút Chơi (28/10/2026) — chip phải nằm trọn bên trái nút.
    chip = visible_chip("fab")
    play = visible_item("instanceAction-fab")
    chip_right = chip.mapToItem(root_item, chip.width(), 0).x()
    assert chip_right <= play.mapToItem(root_item, 0, 0).x(), (chip_right, chip.width())
    press(view, visible_chip("fab"))

    def enabled() -> bool:
        fab = next(i for i in launcher.list_instances() if i.instance_id == "fab")
        return fab.nos_client_enabled

    wait_until(enabled)
