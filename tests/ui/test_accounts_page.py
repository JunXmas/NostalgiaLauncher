"""Trang TÀI KHOẢN với tài khoản Microsoft: hàng nút Làm mới / Tải skin / Slim hiện ra mà
không kéo theo vòng lặp bố cục.

Lỗi thật: `CheckRow` lấy bề rộng theo cha, đặt trong một `Row` (Row rộng theo con) → Qt cảnh
báo "possible QQuickItem::polish() loop" 1.280 lần trong một phiên, CPU quay không, và người
dùng thấy trang "lag". Harness với tài khoản ngoại tuyến không thấy vì hàng nút đó ẩn.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from qml_tree import find_item
from test_qml import make_launcher

from nostalgia.account.model import ELY, MICROSOFT
from nostalgia.account.offline import build_offline_account
from nostalgia.account.store import save_accounts
from nostalgia.api import Launcher
from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def test_microsoft_account_row_does_not_loop_the_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    premium = replace(build_offline_account("JunSlayest"), account_kind=MICROSOFT)
    save_accounts(launcher.paths.accounts_json, (premium,))
    # Tài khoản Microsoft chưa có skin trong cache thì cầu nối tự tải — test không chạm mạng.
    monkeypatch.setattr(Launcher, "refresh_skin", Launcher.describe_skin)

    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        view, _bridge = build_view(launcher)
        view.show()
        root_item = view.rootObject()
        assert root_item is not None
        sidebar = root_item.findChild(QObject, "sidebar")
        assert sidebar is not None
        sidebar.setProperty("currentIndex", 3)
        deadline = time.monotonic() + 0.6
        while time.monotonic() < deadline:
            QGuiApplication.processEvents()
            time.sleep(0.01)
    finally:
        qInstallMessageHandler(None)

    loops = [message for message in warnings if "polish" in message]
    assert loops == [], f"vòng lặp bố cục: {loops[0]}"
    assert warnings == []


def _ely_account_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Dựng trang TÀI KHOẢN với đúng một tài khoản Ely, trả về dòng chữ nhỏ dưới tên."""
    launcher = make_launcher(tmp_path)
    save_accounts(
        launcher.paths.accounts_json,
        (replace(build_offline_account("JunSlayest"), account_kind=ELY),),
    )
    monkeypatch.setattr(Launcher, "refresh_skin", Launcher.describe_skin)
    view, _bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 3)
    QGuiApplication.processEvents()
    detail = find_item(root_item, "accountDetail")
    assert detail is not None
    return str(detail.property("text"))


def test_ely_row_says_when_skins_cannot_show_in_game_yet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skin Ely cần authlib-injector — javaagent JVM, KHÔNG phải mod: launcher tự tải, tự tiêm,
    người dùng không bấm gì. Nhưng "tự động" mà im lặng thì lúc nó hỏng họ chỉ thấy skin biến
    mất và không có chỗ nào để nhìn. Chưa có jar thì hàng tài khoản phải nói ra."""
    assert "đang tải hỗ trợ" in _ely_account_detail(tmp_path, monkeypatch)


def test_ely_row_goes_back_to_the_uuid_once_support_is_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Có jar rồi thì không còn gì để báo — trả chỗ đó lại cho dòng UUID."""
    (tmp_path / "data" / "authlib-injector").mkdir(parents=True)
    (tmp_path / "data" / "authlib-injector" / "authlib-injector-9.9.9.jar").write_bytes(b"PK")
    assert "đang tải hỗ trợ" not in _ely_account_detail(tmp_path, monkeypatch)
