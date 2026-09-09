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
from test_qml import make_launcher

from nostalgia.account.model import MICROSOFT
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
