"""Bấm chọn chỉ xem trước; Lưu mới ghi đúng tài khoản, lỗi giữ bản đang chỉnh."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import Preview, find_control, press
from test_minimal_preview import preview as preview

from nostalgia.account.model import Account
from nostalgia.account.store import save_accounts
from nostalgia.api import Launcher
from nostalgia.errors import SkinError
from nostalgia.skin.capes import OwnedCape
from nostalgia.skin.model import PlayerSkin
from nostalgia.skin.textures import skin_cache_key

pytestmark = pytest.mark.usefixtures("qt_app")


def png(path: Path, color: str, cape: bool = False) -> Path:
    image = QImage(64, 32 if cape else 64, QImage.Format.Format_ARGB32)
    image.fill(QColor(color))
    assert image.save(str(path))
    return path


def account_page(preview: Preview, monkeypatch: pytest.MonkeyPatch, account_kind: str) -> Account:
    launcher, _view, bridge, root_item = preview
    account = Account("SameName", "069a79f4-44e9-4726-a5be-fca90e38aaf5", account_kind)
    monkeypatch.setattr(Launcher, "refresh_skin", lambda self, account: self.describe_skin(account))
    save_accounts(launcher.paths.accounts_json, (account,))
    bridge.announce_accounts_changed()
    bridge.setActiveAccount(account.account_id)
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 3)
    QTest.qWait(100)
    return account


@pytest.mark.parametrize("account_kind", ["microsoft", "ely", "offline"])
def test_preview_and_slim_toggle_do_not_apply_until_save(
    preview: Preview,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    account_kind: str,
) -> None:
    launcher, view, _bridge, root_item = preview
    account = account_page(preview, monkeypatch, account_kind)
    editor = view.rootContext().contextProperty("skinEditor")
    calls = []

    def save_skin(self: Launcher, selected: Account, path: Path, *, slim: bool) -> PlayerSkin:
        calls.append((selected.account_id, path.read_bytes(), slim))
        directory = self.paths.skins_dir
        directory.mkdir(parents=True, exist_ok=True)
        key = skin_cache_key(selected.account_kind, selected.player_name, selected.player_uuid)
        cached = directory / (key + ".png")
        cached.write_bytes(path.read_bytes())
        if slim:
            (directory / (key + ".slim")).touch()
        return self.describe_skin(selected)

    monkeypatch.setattr(Launcher, "save_skin_selection", save_skin)
    original = launcher.describe_skin(account)
    path = png(tmp_path / "custom.png", "#846dd4")
    editor.importSkin(QUrl.fromLocalFile(str(path)).toString())
    wait_until(lambda: editor.details["skinDirty"] and not editor.busy)
    figure = find_control(root_item, "accountSkinFigure")
    wait_until(lambda: figure.property("source") == editor.details["source"])
    assert not calls and launcher.describe_skin(account) == original
    editor.setSlim(False)
    wait_until(lambda: bool(figure.property("atlasReady")))
    before = figure.property("atlas")
    find_control(root_item, "skinSlimToggle").forceActiveFocus()
    QTest.keyClick(view, Qt.Key.Key_Space)
    assert editor.details["slim"] and figure.property("slim")
    wait_until(lambda: figure.property("atlas") != before and bool(figure.property("atlasReady")))
    assert not calls
    press(view, find_control(root_item, "skinSaveButton"))
    wait_until(lambda: not editor.busy and not editor.details["dirty"])
    assert calls == [(account.account_id, path.read_bytes(), True)]
    assert launcher.describe_skin(account).slim
    editor.selectSkin(launcher.list_skin_library()[0].entry_id)
    editor.setSlim(True)
    assert not editor.details["skinDirty"]
    editor.save()
    assert len(calls) == 1


def test_cape_cards_preview_on_body_and_partial_save_retries_only_cape(
    preview: Preview,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _launcher, view, _bridge, root_item = preview
    account = account_page(preview, monkeypatch, "microsoft")
    cape = png(tmp_path / "cape.png", "#f67838", True)
    monkeypatch.setattr(
        Launcher, "list_capes", lambda *_args: (OwnedCape("orange", "Orange", "", False),)
    )
    monkeypatch.setattr(Launcher, "cache_cape_texture", lambda *_args: cape)
    editor = view.rootContext().contextProperty("skinEditor")
    skin_calls, cape_calls = [], []
    monkeypatch.setattr(
        Launcher,
        "save_skin_selection",
        lambda _self, account, _path, **_args: skin_calls.append(account.account_id),
    )

    def save_cape(self: Launcher, selected: Account, cape_id: str) -> PlayerSkin:
        cape_calls.append(cape_id)
        if len(cape_calls) == 1:
            raise SkinError("Cape service unavailable")
        return self.describe_skin(selected)

    monkeypatch.setattr(Launcher, "set_cape", save_cape)
    editor.importSkin(QUrl.fromLocalFile(str(png(tmp_path / "skin.png", "#726bb2"))).toString())
    wait_until(lambda: not editor.busy and editor.details["skinDirty"])
    panel = find_control(root_item, "skinPanel")
    panel.setProperty("tab", "cape")
    capes = view.rootContext().contextProperty("capeBridge")
    wait_until(lambda: len(capes.capes) == 1 and not capes.busy)
    press(view, find_control(root_item, "previewCape-orange"))
    figure = find_control(root_item, "accountSkinFigure")
    assert figure.property("capeSource") == QUrl.fromLocalFile(str(cape)).toString()
    wait_until(lambda: bool(figure.property("atlasReady")))
    card_figure = find_control(root_item, "capeLibraryFigure")
    assert not card_figure.property("interactive") and card_figure.property("previewFrame") == 41
    assert not skin_calls and not cape_calls
    press(view, find_control(root_item, "skinSaveButton"))
    wait_until(lambda: not editor.busy and "cape chưa lưu" in editor.details["note"])
    assert not editor.details["skinDirty"] and editor.details["capeDirty"]
    # Skin đã lưu còn được tải lại qua accountBridge; nút chỉ mở khi refresh xong.
    save_button = find_control(root_item, "skinSaveButton")
    wait_until(lambda: bool(save_button.property("clickable")))
    press(view, save_button)
    wait_until(lambda: not editor.busy and not editor.details["dirty"])
    assert skin_calls == [account.account_id] and cape_calls == ["orange", "orange"]


def test_failed_save_and_account_switch_preserve_each_draft(
    preview: Preview,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher, view, bridge, root_item = preview
    account = account_page(preview, monkeypatch, "ely")
    second = launcher.add_offline_account("Another")
    bridge.announce_accounts_changed()
    editor = view.rootContext().contextProperty("skinEditor")
    editor.importSkin(QUrl.fromLocalFile(str(png(tmp_path / "skin.png", "#38b786"))).toString())
    wait_until(lambda: editor.details["dirty"] and not editor.busy)
    original = editor.details["source"]

    def fail_save(*_args: object, **_kwargs: object) -> None:
        raise SkinError("Login expired")

    monkeypatch.setattr(Launcher, "save_skin_selection", fail_save)
    press(view, find_control(root_item, "skinSaveButton"))
    wait_until(lambda: not editor.busy and "Login expired" in editor.details["note"])
    assert editor.details["dirty"]
    bridge.setActiveAccount(second.account_id)
    wait_until(lambda: editor.details["accountId"] == second.account_id)
    assert not editor.details["dirty"]
    bridge.setActiveAccount(account.account_id)
    wait_until(lambda: editor.details["accountId"] == account.account_id)
    assert editor.details["source"] == original and editor.details["dirty"]
    press(view, find_control(root_item, "skinDiscardButton"))
    assert not editor.details["dirty"]
