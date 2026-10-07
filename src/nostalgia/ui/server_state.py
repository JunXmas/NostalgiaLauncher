"""Qt properties for the server manager. Worker results are applied only on the GUI thread."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from PySide6.QtCore import Property, QObject, Signal

from nostalgia.api import ENGINES, ServerManager
from nostalgia.ui.game_log import GameLogFeed
from nostalgia.ui.worker import WorkerBridge


class ServerState(WorkerBridge):
    changed = Signal()
    selectionLoaded = Signal()
    created = Signal(str)
    configLoaded = Signal()
    contentInstalled = Signal()
    _result = Signal(int, str, object)
    _manager: ServerManager
    _enabled: bool
    _access: bool
    _note: str
    _servers: list[dict[str, Any]]
    _selected: dict[str, Any]
    _game_versions: list[str]
    _builds: list[str]
    _projects: list[dict[str, Any]]
    _content_versions: list[dict[str, Any]]
    _installed: list[dict[str, Any]]
    _config_files: list[str]
    _config_text: str
    _feed: GameLogFeed

    @Property(list, constant=True)
    def engines(self) -> list[dict[str, Any]]:
        return [
            asdict(engine)
            | {
                "plugin_loaders": list(engine.plugin_loaders),
                "supports_plugins": bool(engine.plugin_loaders),
            }
            for engine in ENGINES
        ]

    @Property(bool, notify=changed)
    def enabled(self) -> bool:
        return self._enabled

    @Property(bool, notify=changed)
    def hasAccess(self) -> bool:
        return self._enabled and self._access

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    @Property(list, notify=changed)
    def servers(self) -> list[dict[str, Any]]:
        return self._servers

    @Property(dict, notify=changed)
    def selected(self) -> dict[str, Any]:
        return self._selected

    @Property(list, notify=changed)
    def gameVersions(self) -> list[str]:
        return self._game_versions

    @Property(list, notify=changed)
    def builds(self) -> list[str]:
        return self._builds

    @Property(list, notify=changed)
    def projects(self) -> list[dict[str, Any]]:
        return self._projects

    @Property(list, notify=changed)
    def contentVersions(self) -> list[dict[str, Any]]:
        return self._content_versions

    @Property(list, notify=changed)
    def installed(self) -> list[dict[str, Any]]:
        return self._installed

    @Property(list, notify=changed)
    def configFiles(self) -> list[str]:
        return self._config_files

    @Property(str, notify=changed)
    def configText(self) -> str:
        return self._config_text

    @Property(str, notify=changed)
    def runningId(self) -> str:
        return self._manager.running_id

    @Property(str, notify=changed)
    def readyId(self) -> str:
        return self._manager.ready_id

    @Property(QObject, constant=True)
    def console(self) -> GameLogFeed:
        return self._feed
