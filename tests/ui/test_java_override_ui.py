"""Java nâng cao trong Quản lý bản chơi: ẩn mặc định, sai đường dẫn không lưu, Tự động xoá."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

pytest.importorskip("PySide6")
from qml_tree import find_item
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview
from test_modern_workspace import prepare_instance

from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_advanced_java_is_hidden_validated_and_resettable(preview: Preview, tmp_path: Path) -> None:
    launcher, view, _bridge, root_item = preview
    prepare_instance(preview)
    press(view, find_item(root_item, "manageInstance-survival"))
    dialog = find_control(root_item, "modernInstanceManager")
    wait_until(lambda: bool(dialog.property("opened")))
    press(view, find_item(dialog.property("contentItem"), "instanceSection-2"))
    section = find_control(root_item, "instanceJavaSection")
    assert not section.isVisible(), "bình thường để tự chọn: phần Java phải ẩn"
    press(view, find_control(root_item, "instanceAdvancedToggle"))
    wait_until(section.isVisible)

    field = find_control(root_item, "instanceJava")
    field.setProperty("text", str(tmp_path / "khong-co" / "java"))
    press(view, find_control(root_item, "instanceSave"))
    wait_until(lambda: find_control(root_item, "instanceJavaError").isVisible())
    assert dialog.property("visible"), "đường dẫn sai: giữ hộp mở để sửa"
    assert launcher.list_instances()[0].java_binary_override == ""

    java = tmp_path / "jdk" / "java"
    java.parent.mkdir()
    java.write_text("")
    field.setProperty("text", str(java))
    press(view, find_control(root_item, "instanceSave"))
    wait_until(lambda: not dialog.property("visible"))
    assert launcher.list_instances()[0].java_binary_override == str(java)

    dialog.openFor(cast(Any, _bridge).instances[0])
    wait_until(lambda: bool(dialog.property("opened")))
    assert dialog.property("advanced") is True, "đã chọn Java riêng thì mở sẵn phần nâng cao"
    dialog.setProperty("section", 2)
    press(view, find_control(root_item, "instanceJavaAuto"))
    press(view, find_control(root_item, "instanceSave"))
    wait_until(lambda: not dialog.property("visible"))
    assert launcher.list_instances()[0].java_binary_override == ""
