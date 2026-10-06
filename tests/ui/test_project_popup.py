"""Bấm thẻ mở popup; chọn game/bản phát hành phải cài đúng vào bản chơi tương thích."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import find_control, press

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.installer import ContentInstallReport
from nostalgia.content.model import ContentKind, Project, ProjectDetails, ProjectVersion, SearchPage
from nostalgia.instance.model import Instance
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


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


@pytest.mark.parametrize("content_kind", ["mod", "resourcepack", "shader", "modpack"])
def test_card_popup_selects_version_and_installs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content_kind: ContentKind,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    launcher.add_offline_account("JunPreview")
    for instance_id in ("fabric", "forge", "vanilla"):
        launcher.save_instance(Instance(instance_id, "1.20.1", display_name=instance_id.title()))
    targets = {
        "fabric": ContentTarget("fabric", tmp_path / "fabric", "1.20.1", "fabric"),
        "forge": ContentTarget("forge", tmp_path / "forge", "1.21.1", "forge"),
        "vanilla": ContentTarget("vanilla", tmp_path / "vanilla", "1.20.1", "vanilla"),
    }
    project = Project(
        "demo",
        "demo",
        "Demo",
        "Giới thiệu ngắn",
        "Tác giả",
        content_kind,
        "",
        123,
        4,
        ("fabric", "forge"),
    )
    versions = (
        release("new", "1.20.1", "fabric"),
        release("old", "1.20.1", "fabric"),
        release("forge-new", "1.21.1", "forge"),
    )
    choices: list[InstallChoice] = []
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((project,), 0, 1))
    monkeypatch.setattr(
        Launcher, "describe_content_target", lambda _launcher, instance_id: targets[instance_id]
    )
    monkeypatch.setattr(
        Launcher,
        "fetch_content_details",
        lambda *_a: ProjectDetails(
            "# About\nNội dung đầy đủ", "markdown", "https://modrinth.com/project/demo"
        ),
    )
    monkeypatch.setattr(Launcher, "fetch_versions", lambda *_a: versions)

    def install_content(
        _launcher: Launcher, target: ContentTarget, _project: Project, **kwargs: Any
    ) -> ContentInstallReport:
        choices.append(
            InstallChoice(kwargs.get("version_id", ""), target.game_version, target.instance_id)
        )
        return ContentInstallReport((versions[0],))

    def install_pack(
        _launcher: Launcher, _project: Project, instance_id: str, _label: str, **kwargs: Any
    ) -> Instance:
        choices.append(InstallChoice(kwargs["version_id"], kwargs["game_version"], instance_id))
        return Instance(instance_id, "1.20.1")

    monkeypatch.setattr(Launcher, "install_content", install_content)
    monkeypatch.setattr(Launcher, "install_modpack", install_pack)
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    view, bridge = open_preview(launcher)
    try:
        root_item = view.rootObject()
        view.show()
        view.requestActivate()
        root_item.setProperty("currentIndex", 2)
        library = find_control(root_item, "minimalLibrary")
        library.setProperty("kind", content_kind)
        library.refresh()
        content_bridge = view.rootContext().contextProperty("contentBridge")
        wait_until(lambda: not content_bridge.searching and len(content_bridge.results) == 1)
        QTest.qWait(60)
        card = find_visual(root_item, "projectCard-demo")
        assert card is not None, warnings
        position = card.mapToScene(QPointF(100, 100)).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=position)
        dialog = find_control(root_item, "projectDialog")
        project_bridge = view.rootContext().contextProperty("projectBridge")
        wait_until(
            lambda: bool(dialog.property("opened")) and not project_bridge.details["loading"]
        )
        assert find_control(root_item, "projectAbout").property("text") == "About\nNội dung đầy đủ"
        # Popup covers the whole window, including the navigation, and is centred.
        assert dialog.property("modal")
        assert_mica_alignment(root_item)
        assert dialog.property("x") + dialog.property("width") / 2 == pytest.approx(
            view.width() / 2
        )
        picker = find_control(root_item, "projectVersionPicker")
        wait_until(lambda: bool(picker.property("gameVersion")))
        assert picker.property("gameVersion") == "1.20.1"
        assert picker.property("instanceId") == "fabric"
        game_select = find_control(root_item, "projectGameVersion")
        game_select.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Down)
        wait_until(lambda: picker.property("versionId") == "forge-new")
        assert picker.property("gameVersion") == "1.21.1"
        assert picker.property("instanceId") == "forge"
        QTest.keyClick(view, Qt.Key.Key_Up)
        wait_until(lambda: picker.property("versionId") == "new")
        select = find_control(root_item, "projectRelease")
        select.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Down)
        assert picker.property("versionId") == "old"
        press(view, find_control(root_item, "projectInstall"))
        wait_until(lambda: bool(choices) and not project_bridge.installing)
        assert choices[0].version_id == "old"
        assert choices[0].game_version == "1.20.1"
        if content_kind != "modpack":
            assert choices[0].instance_id == "fabric"
        wait_until(lambda: bool(find_control(root_item, "projectSuccess").property("visible")))
        assert not find_control(root_item, "projectInstall").property("clickable")
        press(view, find_control(root_item, "projectClose"))
        assert not dialog.property("opened")
        # The existing quick-download action stays separate from the card action.
        if content_kind != "modpack":
            content_bridge.selectInstance("fabric")
            library.refresh()
            wait_until(lambda: not content_bridge.searching and len(content_bridge.results) == 1)
            press(view, find_visual(root_item, "projectDownload-demo"))
            wait_until(lambda: len(choices) == 2)
            assert not dialog.property("opened")
            assert choices[1].version_id == ""
        # The same dialog also fits the smallest supported window at 150% text.
        view.resize(1024, 600)
        view.rootContext().contextProperty("settingsBridge").setAppearance(
            150, False, False, True, "vi"
        )
        project_bridge.openProject("demo")
        wait_until(lambda: not project_bridge.details["loading"])
        assert dialog.property("width") < view.width()
        assert dialog.property("height") < view.height()
        assert_mica_alignment(root_item)
        assert not warnings
    finally:
        bridge.cancelSignIn()
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(None)
