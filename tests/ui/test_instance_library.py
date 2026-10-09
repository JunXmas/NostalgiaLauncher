"""Thư viện dùng chung từ quản lý: ghim đúng target, cài có chọn bản và quay lại giữ form."""

from dataclasses import dataclass
from typing import Any, cast

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview
from test_project_popup import find_visual, release

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.installed import LedgerEntry, save_ledger
from nostalgia.content.installer import ContentInstallReport
from nostalgia.content.model import Project, ProjectDetails, SearchPage
from nostalgia.instance.model import Instance
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


@dataclass(frozen=True, slots=True)
class Choice:
    instance_id: str
    content_kind: str
    version_id: str


def prepare(context: Preview, monkeypatch: pytest.MonkeyPatch) -> list[Choice]:
    launcher, _view, bridge, root_item = context
    for instance_id in ("selected", "other"):
        launcher.save_instance(Instance(instance_id, "1.20.1", display_name=instance_id.title()))
    monkeypatch.setattr(
        Launcher,
        "describe_content_target",
        lambda _launcher, instance_id: ContentTarget(
            instance_id, launcher.paths.instance_dir(instance_id), "1.20.1", "fabric"
        ),
    )
    monkeypatch.setattr(
        Launcher,
        "search_content",
        lambda _launcher, _target, content_kind, **_kwargs: SearchPage(
            (
                Project(
                    "demo",
                    "demo",
                    "Demo",
                    "About",
                    "Demo author",
                    content_kind,
                    "",
                    100,
                    1,
                    ("fabric",),
                ),
            ),
            0,
            1,
        ),
    )
    monkeypatch.setattr(
        Launcher,
        "fetch_content_details",
        lambda *_args: ProjectDetails("About", "markdown", "https://example.invalid/demo"),
    )
    versions = (
        release("new", "1.20.1", "fabric"),
        release("wrong-loader", "1.20.1", "forge"),
        release("wrong-game", "1.21.1", "fabric"),
    )
    monkeypatch.setattr(Launcher, "fetch_versions", lambda *_args: versions)
    calls: list[Choice] = []

    def install(
        _launcher: Launcher, target: ContentTarget, project: Project, **kwargs: Any
    ) -> ContentInstallReport:
        calls.append(Choice(target.instance_id, project.content_kind, kwargs.get("version_id", "")))
        directory = (
            target.game_dir
            / {"mod": "mods", "shader": "shaderpacks", "resourcepack": "resourcepacks"}[
                project.content_kind
            ]
        )
        directory.mkdir(exist_ok=True)
        name = "demo.jar" if project.content_kind == "mod" else "demo.zip"
        (directory / name).write_bytes(b"local UI installation fixture")
        save_ledger(directory, {"demo": LedgerEntry("demo", "Demo", "new", "1", name)})
        return ContentInstallReport((versions[0],))

    monkeypatch.setattr(Launcher, "install_content", install)
    bridge.announce_instances_changed()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    manager = find_control(root_item, "modernInstanceManager")
    manager.openFor(
        next(row for row in cast(Any, bridge).instances if row["instanceId"] == "selected")
    )
    wait_until(lambda: manager.property("opened"))
    find_control(root_item, "instanceName").setProperty("text", "Unsaved name")
    manager.setProperty("section", 1)
    wait_until(lambda: find_control(root_item, "instanceAddContent").property("visible"))
    return calls


def browse(context: Preview) -> Any:
    _launcher, view, _bridge, root_item = context
    press(view, find_control(root_item, "instanceAddContent"))
    dialog = find_control(root_item, "instanceLibraryDialog")
    wait_until(lambda: dialog.property("opened"))
    content = view.rootContext().contextProperty("contentBridge")
    wait_until(lambda: not content.busy and len(content.results) == 1)
    return dialog


@pytest.mark.parametrize("content_kind", ["mod", "shader", "resourcepack"])
def test_scoped_project_installs_into_selected_instance_then_returns_to_unsaved_form(
    preview: Preview, monkeypatch: pytest.MonkeyPatch, content_kind: str
) -> None:
    calls = prepare(preview, monkeypatch)
    launcher, view, _bridge, root_item = preview
    installed = find_control(root_item, "modernInstalledContent")
    installed.setProperty("kind", content_kind)
    dialog = browse(preview)
    content = view.rootContext().contextProperty("contentBridge")
    assert content.instanceId == content.browseInstanceId == "selected"
    assert content.selectedGameVersions == ["1.20.1"]
    assert content.selectedLoaders == (["fabric"] if content_kind == "mod" else [])
    assert find_control(root_item, "minimalLibrary").property("kind") == content_kind
    assert root_item.findChild(type(installed), "libraryKind-modpack") is None
    content.selectInstance("other")
    content.clearGameVersions()
    content.clearLoaders()
    assert content.instanceId == "selected" and content.selectedGameVersions == ["1.20.1"]
    QTest.qWait(100)
    press(view, find_visual(dialog.property("contentItem"), "projectCard-demo"))
    project = view.rootContext().contextProperty("projectBridge")
    popup = find_control(root_item, "projectDialog")
    wait_until(lambda: popup.property("opened") and not project.details["loading"])
    picker = find_control(root_item, "projectVersionPicker")
    wait_until(lambda: picker.property("canInstall"))
    assert popup.property("z") > dialog.property("z")
    assert picker.property("instanceId") == "selected"
    assert picker.property("gameChoices").toVariant() == ["1.20.1"]
    assert {row["versionId"] for row in picker.property("releases").toVariant()} == (
        {"new"} if content_kind == "mod" else {"new", "wrong-loader"}
    )
    assert not find_control(root_item, "projectTarget").property("enabled")
    project.installVersion("new", "1.20.1", "other", "")
    assert not calls
    press(view, find_control(root_item, "projectInstall"))
    wait_until(lambda: bool(calls) and not project.installing)
    assert calls == [Choice("selected", content_kind, "new")]
    assert not tuple(launcher.paths.instance_dir("other").glob("**/demo.*"))
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: not popup.property("opened"))
    press(view, find_control(root_item, "instanceLibraryBack"))
    wait_until(lambda: not dialog.property("opened"))
    assert not content.browseInstanceId
    assert find_control(root_item, "modernInstanceManager").property("opened")
    assert find_control(root_item, "instanceName").property("text") == "Unsaved name"
    assert content.installed[0]["projectId"] == "demo"
    wait_until(lambda: find_control(root_item, "instanceAddContent").property("activeFocus"))


def test_cancel_and_normal_library_keep_full_modpack_catalog(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = prepare(preview, monkeypatch)
    _launcher, view, _bridge, root_item = preview
    dialog = browse(preview)
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: not dialog.property("opened"))
    assert not calls
    find_control(root_item, "modernInstanceManager").close()
    root_item.setProperty("currentIndex", 2)
    content = view.rootContext().contextProperty("contentBridge")
    wait_until(lambda: not content.busy and content.results[0]["contentKind"] == "modpack")
    assert not content.browseInstanceId and content.selectedGameVersions == []
    assert find_control(root_item, "libraryKind-modpack").property("visible")
    content.selectInstance("other")
    assert content.instanceId == "other"


@pytest.mark.parametrize("scale", [100, 150])
def test_small_scoped_library_has_scrollable_content_and_complete_back_button(
    preview: Preview, monkeypatch: pytest.MonkeyPatch, scale: int
) -> None:
    prepare(preview, monkeypatch)
    _launcher, view, _bridge, root_item = preview
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, False, False, "vi"
    )
    dialog = browse(preview)
    assert dialog.property("width") <= 984 and dialog.property("height") <= 560
    scroll = find_control(root_item, "libraryScroll")
    assert scroll.property("height") > 150
    card = find_visual(dialog.property("contentItem"), "projectCard-demo")
    assert card.height() <= scroll.property("height")
    assert find_control(root_item, "instanceLibraryBack").property("width") <= 936
