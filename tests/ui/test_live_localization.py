"""Live switching in production dialogs, status text, welcome and native menus."""

from typing import Any

import pytest
from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QSystemTrayIcon
from test_bridges import wait_until
from test_minimal_preview import Preview, find_control
from test_minimal_preview import preview as preview

from nostalgia.ui.app import QML_DIR
from nostalgia.ui.preview import open_preview

pytestmark = pytest.mark.usefixtures("qt_app")


def language(preview: Preview, selected: str) -> None:
    _launcher, view, _bridge, _root_item = preview
    settings = view.rootContext().contextProperty("settingsBridge")
    settings.setAppearance(100, False, True, False, selected)


def test_welcome_language_saved_and_native_menu_updates(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    welcome = find_control(root_item, "minimalLogin")
    picker = find_control(welcome, "welcomeLanguagePicker")
    picker.choose(1, False)
    wait_until(lambda: launcher.load_settings().language == "en")
    assert find_control(welcome, "loginMicrosoft").property("label") == "Continue with Microsoft"
    tray = view.findChild(QSystemTrayIcon)
    assert tray is not None and tray.contextMenu() is not None
    assert [
        action.text() for action in tray.contextMenu().actions() if not action.isSeparator()
    ] == ["Show Launcher", "Stop game", "Quit"]
    returning, _ = open_preview(launcher)
    try:
        assert find_control(returning.rootObject(), "loginMicrosoft").property("label") == (
            "Continue with Microsoft"
        )
    finally:
        returning.close()
        returning.deleteLater()
    view.resize(1024, 600)
    settings = view.rootContext().contextProperty("settingsBridge")
    settings.setAppearance(150, False, True, False, "en")
    QTest.qWait(100)
    actions = find_control(welcome, "welcomeActions")
    card = find_control(welcome, "loginCard")
    assert card.property("y") >= actions.property("y") + actions.property("height") + 12
    language(preview, "vi")
    assert find_control(welcome, "loginMicrosoft").property("label") == "Tiếp tục với Microsoft"


def test_open_dialog_guides_and_errors_switch_without_losing_input(preview: Preview) -> None:
    _launcher, _view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    dialog = find_control(root_item, "modernImportDialog")
    dialog.openDialog()
    wait_until(lambda: dialog.property("opened"))
    dialog.setProperty(
        "failure", "Không tìm thấy phiên bản loader. Hãy cài lại loader trước khi chia sẻ."
    )
    language(preview, "en")
    assert dialog.property("title") == "Import instance"
    assert find_control(dialog, "importStatus").property("text") == (
        "Loader version not found. Reinstall the loader before sharing."
    )
    guides = find_control(root_item, "guideDialog")
    guides.openFor("backup")
    wait_until(lambda: guides.property("opened"))
    assert guides.property("title") == "How to use · Export modpacks & data"
    picker = find_control(guides, "guideTopicPicker")
    assert picker.property("displayText") == "Export modpacks & data"
    language(preview, "vi")
    assert guides.property("title") == "Cách dùng · Xuất modpack & dữ liệu"
    assert dialog.property("failure").startswith("Không tìm thấy phiên bản loader.")
    assert dialog.property("opened")


def test_all_production_pages_switch_without_qml_warnings(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        view.resize(1024, 600)
        for selected in ("en", "vi"):
            language(preview, selected)
            for page_index in (0, 1, 2, 3, 4, 5, 6, 7):
                root_item.setProperty("currentIndex", page_index)
                QTest.qWait(100)
                assert find_control(root_item, "minimalPageLoader").property("item")
    finally:
        qInstallMessageHandler(None)
    assert not warnings, warnings


def test_message_parameters_unknown_logs_and_bidirectional_dialog_labels() -> None:
    engine = QQmlEngine()
    qml_definition = QQmlComponent(engine)
    qml_definition.setData(
        b"""import QtQuick
import "." as Local
Item {
    function language(value) { Local.Tr.setLanguage(value); }
    function message(value) { return Local.Tr.message(value); }
    function plural(value, count) { return Local.Tr.plural(value, count); }
    function format(value, arguments) { return Local.Tr.format(value, arguments); }
}""",
        QUrl.fromLocalFile(str(QML_DIR / "LocalizationProbe.qml")),
    )
    probe: Any = qml_definition.create()
    assert probe is not None, [error.toString() for error in qml_definition.errors()]
    try:
        probe.language("en")
        assert probe.message("không thấy file C:\\Games\\Thế giới\\mod{7}.jar") == (
            "File not found: C:\\Games\\Thế giới\\mod{7}.jar"
        )
        assert probe.message(
            "tên người chơi Bản chơi không hợp lệ: cần 3-16 ký tự, "
            "chỉ gồm chữ cái, chữ số và dấu gạch dưới"
        ) == ("Invalid player name Bản chơi: use 3\u201316 letters, digits or underscores")
        assert probe.message("Log latest.log: sodium cần minecraft >=1.21") == (
            "Log latest.log: sodium requires minecraft >=1.21"
        )
        assert probe.message("lỗi không lường trước: Không có quyền với tài khoản này.") == (
            "Unexpected error: No access to this account."
        )
        assert probe.message("[ERROR] mod Ω failed: custom raw diagnostic") == (
            "[ERROR] mod Ω failed: custom raw diagnostic"
        )
        assert probe.format("Tháng sử dụng: %1 · %2", [6, "Pro %1"]) == "6 months of Pro %1"
        assert probe.plural(" kết quả", 1) == " result"
        assert probe.plural(" kết quả", 2) == " results"
        probe.language("vi")
        assert probe.message("Sign out of Google") == "Đăng xuất Google"
        assert probe.message("File not found: C:\\Games\\Thế giới\\mod{7}.jar") == (
            "Không thấy file C:\\Games\\Thế giới\\mod{7}.jar"
        )
    finally:
        probe.deleteLater()
        engine.deleteLater()
