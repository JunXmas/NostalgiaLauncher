"""Danh sách tìm kiếm phải đến luồng Qt trước cờ rảnh; trang cũ xếp hàng phải bị bỏ."""

import threading
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtGui import QGuiApplication
from test_bridges import wait_until

from nostalgia.api import Launcher
from nostalgia.content.model import Project, SearchPage
from nostalgia.errors import NostalgiaError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


def result_page(title: str, total: int) -> SearchPage:
    return SearchPage((Project("demo", "demo", title, "", "", "mod", "", 0, 0, ()),), 0, total)


@pytest.mark.parametrize("fail", [False, True])
def test_search_stays_pending_until_the_gui_receives_results_or_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")

    def search(*_args: Any, **_kwargs: Any) -> SearchPage:
        if fail:
            raise NostalgiaError("Search unavailable")
        return result_page("New search", 3)

    monkeypatch.setattr(Launcher, "search_content", search)
    content = ContentBridge(launcher, LauncherBridge(launcher))
    failures: list[str] = []
    changes: list[tuple[bool, int]] = []
    content.failed.connect(failures.append)
    content.searchingChanged.connect(
        lambda: changes.append((bool(content.searching), threading.get_ident()))
    )
    content.search("mod", "new", "relevance")
    wait_for_background()
    assert content.searching and not content.results and content.property("totalHits") == 0
    wait_until(lambda: not content.searching and not content.busy)
    assert changes == [(True, threading.get_ident()), (False, threading.get_ident())]
    if fail:
        assert failures == ["Search unavailable"] and not content.results
    else:
        assert content.property("results")[0]["title"] == "New search"
        assert content.property("totalHits") == 3


def test_queued_old_page_cannot_replace_a_new_search_or_clear_its_pending_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    entered, release = threading.Event(), threading.Event()

    def search(*_args: Any, **kwargs: Any) -> SearchPage:
        if kwargs["query"] == "new":
            entered.set()
            assert release.wait(3)
        return result_page(kwargs["query"], 2 if kwargs["query"] == "new" else 1)

    monkeypatch.setattr(Launcher, "search_content", search)
    content = ContentBridge(launcher, LauncherBridge(launcher))
    try:
        content.search("mod", "old", "relevance")
        wait_for_background()
        # Trang cũ đã về nhưng chưa chạy event Qt; bắt đầu tìm mới ngay.
        content.search("mod", "new", "relevance")
        assert entered.wait(2)
        QGuiApplication.processEvents()
        assert not content.results and content.property("totalHits") == 0 and content.searching
        release.set()
        wait_until(lambda: not content.searching and not content.busy)
        assert content.property("results")[0]["title"] == "new"
        assert content.property("totalHits") == 2
    finally:
        release.set()
        wait_for_background()
