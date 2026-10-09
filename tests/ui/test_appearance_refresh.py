"""Làm mới cape ở cùng đường dẫn phải thay ảnh 3D, không trả lại atlas cũ."""

import pytest
from PySide6.QtGui import QColor, QImage
from test_bridges import wait_until
from test_minimal_preview import Preview, find_control
from test_minimal_preview import preview as preview

pytestmark = pytest.mark.usefixtures("qt_app")


def test_refresh_of_same_cape_path_changes_preview_cache_key(preview: Preview) -> None:
    launcher, view, bridge, root_item = preview
    account = launcher.add_offline_account("RefreshPreview")
    directory = launcher.paths.skins_dir
    directory.mkdir(parents=True, exist_ok=True)
    key = account.player_uuid.replace("-", "")
    skin = QImage(64, 64, QImage.Format.Format_ARGB32)
    skin.fill(QColor("#579eae"))
    cape = QImage(64, 32, QImage.Format.Format_ARGB32)
    cape.fill(QColor("#f59a51"))
    assert skin.save(str(directory / (key + ".png")))
    cape_path = directory / (key + ".cape.png")
    assert cape.save(str(cape_path))
    bridge.announce_accounts_changed()
    bridge.setActiveAccount(account.account_id)
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 3)
    figure = find_control(root_item, "accountSkinFigure")
    wait_until(lambda: bool(figure.property("atlasReady")))
    before = figure.property("atlas")
    cape.fill(QColor("#766cbd"))
    assert cape.save(str(cape_path))
    view.rootContext().contextProperty("accountBridge")._skinsRefreshed.emit()
    wait_until(lambda: figure.property("atlas") != before and bool(figure.property("atlasReady")))
    assert not view.rootContext().contextProperty("skinEditor").details["dirty"]
