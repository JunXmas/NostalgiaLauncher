"""Thu hồi cửa sổ trên luồng Qt sau mỗi test, trước khi GC chạy ở worker nền."""

import gc

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from shiboken6 import isValid

from nostalgia.ui.worker import wait_for_background


def finish_windows(application: QGuiApplication) -> None:
    windows = list(application.topLevelWindows())
    for window in windows:
        if not isValid(window):
            continue
        window.close()
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
    gc.collect()
