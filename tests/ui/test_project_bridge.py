"""Lỗi, yêu cầu về muộn và thao tác cài popup không được lẫn dự án/phiên bản."""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6")
from test_bridges import wait_until
from test_project_popup import release

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.installer import ContentInstallReport
from nostalgia.content.model import Project, ProjectDetails
from nostalgia.errors import NetworkError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.project_bridge import ProjectBridge
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


def project(project_id: str) -> Project:
    return Project(
        project_id, project_id, project_id, "summary", "author", "mod", "", 1, 1, ("fabric",)
    )


@pytest.mark.parametrize("late_failure", [False, True])
def test_late_project_response_does_not_replace_the_new_popup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    late_failure: bool,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.resultsModel.reset([project("first"), project("second")])
    popup = ProjectBridge(launcher, LauncherBridge(launcher), content_bridge)
    started, resume = threading.Event(), threading.Event()

    def fetch_details(_launcher: Launcher, selected: Project) -> ProjectDetails:
        if selected.project_id == "first":
            started.set()
            assert resume.wait(3)
            if late_failure:
                raise ValueError("late network failure")
        return ProjectDetails(selected.title, "markdown", "")

    monkeypatch.setattr(Launcher, "fetch_content_details", fetch_details)
    monkeypatch.setattr(
        Launcher, "fetch_versions", lambda *_args: (release("v1", "1.20.1", "fabric"),)
    )
    try:
        popup.openProject("first")
        wait_until(started.is_set)
        popup.openProject("second")
        wait_until(lambda: not popup.details["loading"])
        assert popup.details["title"] == "second"
        resume.set()
        wait_for_background()
        wait_until(lambda: not popup.busy)
        assert popup.details["about"] == "second"
        assert not popup.details["error"]
    finally:
        resume.set()
        wait_for_background()


def test_failed_version_request_retries_even_after_search_results_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.resultsModel.reset([project("demo")])
    popup = ProjectBridge(launcher, LauncherBridge(launcher), content_bridge)
    requests = []

    def fetch_versions(*_args: Any) -> tuple[Any, ...]:
        requests.append(True)
        if len(requests) == 1:
            raise NetworkError("offline")
        return (release("v1", "1.20.1", "fabric"),)

    def fetch_details(*_args: Any) -> ProjectDetails:
        raise NetworkError("about unavailable")

    monkeypatch.setattr(Launcher, "fetch_versions", fetch_versions)
    monkeypatch.setattr(Launcher, "fetch_content_details", fetch_details)
    popup.openProject("demo")
    wait_until(lambda: not popup.details["loading"])
    assert popup.details["error"] == "offline"
    content_bridge.resultsModel.reset([])
    popup.reload()
    wait_until(lambda: not popup.details["loading"])
    assert len(popup.details["versions"]) == 1
    assert popup.details["notice"]
    assert popup.details["about"] == "summary"
    assert not popup.details["error"]
    wait_for_background()


def test_popup_rejects_incompatible_target_and_duplicate_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.resultsModel.reset([project("demo"), project("other")])
    popup = ProjectBridge(launcher, LauncherBridge(launcher), content_bridge)
    monkeypatch.setattr(
        Launcher, "fetch_content_details", lambda *_args: ProjectDetails("about", "markdown", "")
    )
    monkeypatch.setattr(
        Launcher, "fetch_versions", lambda *_args: (release("v1", "1.20.1", "fabric"),)
    )
    target = ContentTarget("chosen", tmp_path / "chosen", "1.20.1", "forge")
    monkeypatch.setattr(Launcher, "describe_content_target", lambda *_args: target)
    popup.openProject("demo")
    wait_until(lambda: not popup.details["loading"])
    popup.installVersion("v1", "1.20.1", "chosen", "")
    wait_until(lambda: bool(popup.details["error"]) and not popup.installing)
    assert "incompatible" in popup.details["error"]
    target = replace(target, loader_kind="fabric")
    calls = []
    resume = threading.Event()

    def install(*_args: Any, **kwargs: Any) -> ContentInstallReport:
        calls.append(kwargs["version_id"])
        assert resume.wait(3)
        return ContentInstallReport(())

    monkeypatch.setattr(Launcher, "install_content", install)
    try:
        popup.installVersion("v1", "1.20.1", "chosen", "")
        wait_until(lambda: bool(calls))
        popup.installVersion("v1", "1.20.1", "chosen", "")
        popup.openProject("other")
        assert popup.details["projectId"] == "demo"
        assert calls == ["v1"]
        resume.set()
        wait_until(lambda: not popup.installing and not popup.details["error"])
    finally:
        resume.set()
        wait_for_background()
