"""Thu hồi cửa sổ trên luồng Qt sau mỗi test, trước khi GC chạy ở worker nền."""

import gc
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from shiboken6 import isValid

from nostalgia.ui.worker import wait_for_background


def retain_windows(monkeypatch: pytest.MonkeyPatch) -> list[QQuickView]:
    windows: list[QQuickView] = []
    original_init = QQuickView.__init__

    def retained_init(view: QQuickView, *args: Any, **kwargs: Any) -> None:
        original_init(view, *args, **kwargs)
        windows.append(view)

    monkeypatch.setattr(QQuickView, "__init__", retained_init)
    return windows


def finish_windows(application: QGuiApplication, windows: list[QQuickView]) -> None:
    for window in windows:
        if not isValid(window):
            continue
        window.close()
        # Gỡ cây QML khi cầu nối còn sống; DeferredDelete không bảo đảm thứ tự huỷ
        # các QObject con và có thể để Connections cũ báo lỗi trong test kế tiếp.
        window.setSource(QUrl())
        for timer in window.findChildren(QTimer):
            timer.stop()
        if isinstance(window, QQuickView):
            for bridge_name in (
                "hostBridge",
                "multiplayerBridge",
                "presenceBridge",
                "socialBridge",
                "serverBridge",
            ):
                bridge = window.rootContext().contextProperty(bridge_name)
                if bridge is not None and isValid(bridge):
                    stop = getattr(bridge, "shutdown", None) or getattr(bridge, "stop", None)
                    if stop:
                        stop()
    wait_for_background()
    for window in windows:
        if isValid(window):
            window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()
    windows.clear()
    gc.collect()
