"""Shared project-popup fixtures and visual assertions."""

from dataclasses import dataclass
from typing import Any

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtTest import QTest
from test_minimal_preview import find_control

from nostalgia.content.model import ProjectVersion


@dataclass(frozen=True, slots=True)
class InstallChoice:
    version_id: str
    game_version: str
    instance_id: str


def release(version_id: str, game_version: str, loader_kind: str) -> ProjectVersion:
    return ProjectVersion(
        version_id,
        "demo",
        version_id,
        "release",
        (game_version,),
        (loader_kind,),
        "2026-01-01",
        "https://example.invalid/file",
        "mod.jar",
        "0" * 40,
        1,
        (),
    )


def find_visual(root_item: Any, name: str) -> Any:
    if root_item.objectName() == name:
        return root_item
    for child in root_item.childItems():
        result = find_visual(child, name)
        if result is not None:
            return result
    return None


def assert_mica_alignment(root_item: Any) -> None:
    QTest.qWait(30)
    mica = find_control(root_item, "projectMica")
    origin = mica.mapToScene(QPointF())
    assert mica.property("backdropRect").x() == pytest.approx(origin.x())
    assert mica.property("backdropRect").y() == pytest.approx(origin.y())
