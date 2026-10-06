"""Run the isolated UI design preview without building or changing release UI.

    python bench/ui_minimal_preview.py
    python bench/ui_minimal_preview.py --data-dir /path/to/preview-data

By default data and settings live in a temporary directory. No game data is copied.
"""

from __future__ import annotations

import argparse
import tempfile
from dataclasses import replace
from pathlib import Path

from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication

from nostalgia.api import Launcher
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    preview_dir = args.data_dir or Path(tempfile.mkdtemp(prefix="nostalgia-ui-preview-"))
    launcher = Launcher.for_data_dir(preview_dir / "data", preview_dir / "settings")
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    qt_application = QApplication(["Nostalgia UI preview"])
    qt_application.setApplicationName("Nostalgia UI preview")
    view, bridge = open_preview(launcher)
    try:
        if view.status() != QQuickView.Status.Ready:
            for error in view.errors():
                print(error.toString())
            return 1
        # First launch fills the desktop while keeping standard window controls.
        if bridge.activePlayerName:
            view.show()
        else:
            view.showMaximized()
        return qt_application.exec()
    finally:
        bridge.cancelSignIn()
        wait_for_background()


if __name__ == "__main__":
    raise SystemExit(main())
