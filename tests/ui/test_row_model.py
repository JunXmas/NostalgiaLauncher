"""KeyedRowModel: đồng bộ tối thiểu — gỡ, sửa, nối — không bao giờ reset."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from nostalgia.ui.row_model import KeyedRowModel

pytestmark = pytest.mark.usefixtures("qt_app")


def make(rows: list[tuple[str, bool]]) -> list[dict[str, object]]:
    return [{"fileName": name, "enabled": enabled} for name, enabled in rows]


def test_sync_emits_only_minimal_changes() -> None:
    model = KeyedRowModel(("fileName", "enabled"), key="fileName")
    events: list[str] = []
    model.modelReset.connect(lambda: events.append("reset"))
    model.rowsInserted.connect(lambda _p, first, last: events.append(f"insert {first}-{last}"))
    model.rowsRemoved.connect(lambda _p, first, last: events.append(f"remove {first}-{last}"))
    model.dataChanged.connect(lambda top, _bottom: events.append(f"change {top.row()}"))

    model.sync(make([("a.jar", True), ("b.jar", True), ("c.jar", True)]))
    assert events == ["insert 0-2"]

    events.clear()
    model.sync(make([("a.jar", False), ("c.jar", True), ("d.jar", True)]))  # b gỡ, a đổi, d mới
    assert events == ["remove 1-1", "change 0", "insert 2-2"]
    assert [row["fileName"] for row in model.rows] == ["a.jar", "c.jar", "d.jar"]
    assert model.rows[0]["enabled"] is False

    events.clear()
    model.sync(make([("a.jar", False), ("c.jar", True), ("d.jar", True)]))
    assert events == [], "không đổi gì thì không phát gì"
