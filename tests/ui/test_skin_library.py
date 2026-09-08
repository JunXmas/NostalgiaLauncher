"""Thư viện skin trong launcher: nhập file vào kho, dùng cho tài khoản ngoại tuyến đổi ngay
trong launcher, thẻ "Đang dùng" khớp theo khoá ảnh, gỡ khỏi kho; lưới QML vẽ được."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject, QUrl
from test_bridges import wait_until
from test_qml import make_launcher

from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.app import build_view
from nostalgia.ui.bridge import LauncherBridge

pytestmark = pytest.mark.usefixtures("qt_app")

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def test_import_apply_and_remove_through_the_bridge(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.add_offline_account("Jun")
    main_bridge = LauncherBridge(launcher)
    account_bridge = AccountBridge(launcher, main_bridge)
    assert account_bridge.skinLibrary == []

    skin_file = tmp_path / "ao-xanh.png"
    skin_file.write_bytes(PNG_HEADER + b"xanh")
    account_bridge.importSkin(QUrl.fromLocalFile(str(skin_file)).toString(), True)
    wait_until(lambda: len(account_bridge.skinLibrary) == 1 and not account_bridge.busy)
    [row] = account_bridge.skinLibrary
    assert (row["name"], row["slim"], row["sourceLabel"]) == ("ao-xanh", True, "Tự nhập")
    assert row["skinFile"].startswith("file://")
    assert account_bridge.accountNamed("Jun")["skinDigest"] == "", "chưa dùng skin nào"

    applied: list[str] = []
    account_bridge.skinUploaded.connect(applied.append)
    account_bridge.applyLibrarySkin("Jun", row["entryId"])
    wait_until(lambda: applied == ["Jun"] and not account_bridge.busy)
    wait_until(lambda: account_bridge.accountNamed("Jun")["skinDigest"] == row["entryId"])
    shown = account_bridge.accountNamed("Jun")
    assert shown["slim"] is True and shown["isDefaultSkin"] is False
    assert Path(QUrl(shown["skinFile"]).toLocalFile()).read_bytes() == skin_file.read_bytes()

    account_bridge.removeLibrarySkin(row["entryId"])
    assert account_bridge.skinLibrary == []
    assert account_bridge.accountNamed("Jun")["isDefaultSkin"] is False, (
        "gỡ khỏi kho không đụng skin đang dùng"
    )


def test_library_grid_renders_entries(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.add_offline_account("Jun")
    for number in range(3):
        png = tmp_path / f"skin-{number}.png"
        png.write_bytes(PNG_HEADER + bytes([number]))
        launcher.import_skin(png, name=f"Skin {number}")
    view, _bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 3)
    wait_until(lambda: root_item.findChild(QObject, "skinLibraryGrid") is not None)
    grid = root_item.findChild(QObject, "skinLibraryGrid")
    assert grid is not None

    # Flow chứa cả Repeater lẫn 3 thẻ nó sinh ra; chỉ đếm thẻ (Rectangle).
    def card_count() -> int:
        return sum(
            1 for child in grid.childItems() if "Rectangle" in child.metaObject().className()
        )

    wait_until(lambda: card_count() == 3)
    import_button = root_item.findChild(QObject, "importSkinButton")
    assert import_button is not None and import_button.property("visible") is True
