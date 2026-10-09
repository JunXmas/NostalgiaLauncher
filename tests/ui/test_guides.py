"""Hướng dẫn không sửa dữ liệu; GIF dừng/giải phóng khi ẩn, bố cục nhỏ không tràn."""

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QObject, QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QImageReader
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import Preview, find_control, press
from test_minimal_preview import preview as preview

pytestmark = pytest.mark.usefixtures("qt_app")


def guide(preview: Preview, topic_id: str = "appearance") -> tuple[Any, QObject]:
    _launcher, _view, _bridge, root_item = preview
    dialog = find_control(root_item, "guideDialog")
    dialog.openFor(topic_id)
    wait_until(lambda: dialog.property("opened"))
    animation = find_control(root_item, "guideAnimation")
    wait_until(lambda: find_control(root_item, "guideMedia").property("ready"))
    return dialog, animation


def test_guide_from_login_and_f1_never_signs_in_or_changes_accounts(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    login = find_control(root_item, "minimalLogin")
    press(view, find_control(login, "guideButton-start"))
    dialog = find_control(root_item, "guideDialog")
    wait_until(lambda: dialog.property("opened"))
    assert dialog.property("topicId") == "start"
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: not dialog.property("visible"))
    assert root_item.property("loginVisible") and not launcher.list_accounts()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    wait_until(lambda: not root_item.property("loginVisible"))
    press(view, root_item, Qt.Key.Key_F1)
    wait_until(lambda: dialog.property("opened"))
    assert dialog.property("topicId") == "create"
    assert not launcher.list_instances() and not launcher.list_accounts()


def test_gif_pause_reduced_motion_hidden_window_and_close(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    dialog, animation = guide(preview)
    wait_until(lambda: animation.property("playing"))
    first_frame = animation.property("currentFrame")
    wait_until(lambda: animation.property("currentFrame") != first_frame)
    press(view, find_control(root_item, "guidePause"))
    assert not animation.property("playing")
    paused_frame = animation.property("currentFrame")
    QTest.qWait(350)
    assert animation.property("currentFrame") == paused_frame
    press(view, find_control(root_item, "guidePause"))
    wait_until(lambda: animation.property("playing"))
    settings = view.rootContext().contextProperty("settingsBridge")
    settings.setAppearance(100, False, True, False, "vi")
    wait_until(lambda: not animation.property("playing"))
    assert animation.property("source").toString().endswith("appearance.gif")
    settings.setAppearance(100, False, False, False, "vi")
    view.hide()
    wait_until(lambda: not animation.property("playing"))
    view.show()
    view.requestActivate()
    wait_until(lambda: animation.property("playing"))
    dialog.close()
    wait_until(lambda: not animation.property("source").toString())


def test_help_over_import_keeps_underlying_form_and_keyboard_focus(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    QTest.qWait(100)
    imports = find_control(root_item, "modernImportDialog")
    imports.openDialog()
    wait_until(lambda: imports.property("opened"))
    imports.setProperty("section", 1)
    help_button = find_control(root_item, "guideButton-import")
    press(view, help_button)
    dialog = find_control(root_item, "guideDialog")
    wait_until(lambda: dialog.property("opened"))
    assert dialog.property("z") > imports.property("z")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: not dialog.property("opened"))
    assert imports.property("opened") and imports.property("section") == 1
    wait_until(lambda: help_button.property("activeFocus"))


def test_guides_search_and_small_scaled_layout_have_no_qml_errors(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    warnings: list[str] = []
    previous = qInstallMessageHandler(lambda _mode, _context, message: warnings.append(message))
    try:
        dialog, _animation = guide(preview)
        query = find_control(root_item, "guideSearch")
        query.setProperty("text", "dong bo")
        QTest.qWait(80)
        button = find_control(root_item, "guideTopic-host")
        press(view, button)
        assert dialog.property("topicId") == "host"
        wait_until(lambda: find_control(root_item, "guideMedia").property("ready"))
        query.setProperty("text", "")
        picker = find_control(root_item, "guideTopicPicker")
        press(view, picker, Qt.Key.Key_Space)
        menu = find_control(root_item, "guideTopicPickerMenu")
        wait_until(lambda: menu.property("opened"))
        find_control(root_item, "guideTopicPickerSearch").setProperty("text", "Skin")
        QTest.keyClick(view, Qt.Key.Key_Return)
        wait_until(lambda: dialog.property("topicId") == "appearance")
        for scale, width, height in [(100, 1440, 900), (150, 1024, 600)]:
            view.resize(width, height)
            view.rootContext().contextProperty("settingsBridge").setAppearance(
                scale, False, False, False, "vi"
            )
            QTest.qWait(200)
            assert dialog.property("width") <= width - 38
            assert dialog.property("height") <= height - 38
            scroll = find_control(root_item, "guideScroll")
            assert scroll.property("height") > 100
            assert scroll.property("contentWidth") <= scroll.property("width")
            for name in ["guideSearch", "guideTopicPicker"]:
                control = find_control(root_item, name)
                origin = control.mapToScene(QPointF())
                assert origin.x() >= 0 and origin.x() + control.width() <= width
        dialog.close()
    finally:
        qInstallMessageHandler(previous)
    assert not [
        text
        for text in warnings
        if any(
            marker in text
            for marker in (
                "ReferenceError",
                "TypeError",
                "Binding loop",
                "Cannot",
                "Unable",
                "Error decoding",
            )
        )
    ]


def test_packaged_gifs_decode_offline_and_have_bounded_sizes() -> None:
    directory = Path(__file__).resolve().parents[2] / "src/nostalgia/ui/qml/assets/guides"
    paths = tuple(directory.glob("*.gif"))
    assert len(paths) == 17
    assert sum(path.stat().st_size for path in paths) <= 5 * 1024**2
    for path in paths:
        reader = QImageReader(str(path))
        assert reader.supportsAnimation() and reader.imageCount() > 1
        assert reader.size().width() <= 720 and reader.size().height() <= 500
        assert not reader.read().isNull()
        assert path.stat().st_size < 512 * 1024
