"""Tín hiệu QML vẫn hoạt động sau GC và hết sống khi đóng cửa sổ."""

import gc
import weakref
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QUrl, Signal
from shiboken6 import isValid

from nostalgia.ui.view import LauncherView

pytestmark = pytest.mark.usefixtures("qt_app")


class PopupBridge(QObject):
    requested = Signal()


def test_popup_signal_survives_gc_until_view_is_destroyed(tmp_path: Path) -> None:
    qml = tmp_path / "Popup.qml"
    qml.write_text(
        "import QtQuick\n"
        "Item { id: root; property bool requested: false; Connections { target: popupBridge; "
        "function onRequested() { root.requested = true; } } }"
    )
    view = LauncherView()
    bridge = PopupBridge(view)
    reference = weakref.ref(bridge)
    view.bind_context_property("popupBridge", bridge)
    view.setSource(QUrl.fromLocalFile(str(qml)))
    assert view.status() == LauncherView.Status.Ready
    del bridge
    gc.collect()
    active_bridge = reference()
    assert active_bridge is not None
    active_bridge.requested.emit()
    assert view.rootObject().property("requested")
    del active_bridge
    view.setSource(QUrl())
    view.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del view
    gc.collect()
    assert reference() is None or not isValid(reference())
