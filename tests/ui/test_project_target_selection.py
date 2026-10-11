"""Bản chơi quyết định bản cài; chuyển đích không giữ nhầm phiên bản thủ công."""

from dataclasses import replace
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_instance_library import prepare
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.api import ContentTarget, Launcher
from nostalgia.instance.model import Instance
from nostalgia.modloader.model import LoaderKind
from project_popup_fixture import release
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def configure(context: Preview, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any, list[Any]]:
    launcher, view, bridge, root_item = context
    calls = prepare(context, monkeypatch)
    find_control(root_item, "modernInstanceManager").close()
    specifications: tuple[tuple[str, str, LoaderKind], ...] = (
        ("selected", "1.20.1", "fabric"),
        ("other", "1.20.1", "fabric"),
        ("forge", "1.21.1", "forge"),
        ("neoforge", "1.21.1", "neoforge"),
        ("quilt", "1.20.1", "quilt"),
        ("vanilla", "1.20.1", "vanilla"),
        ("unsupported", "1.19.4", "fabric"),
        ("beta-only", "1.18.2", "fabric"),
    )
    targets = {
        name: ContentTarget(name, launcher.paths.instance_dir(name), game, loader_kind)
        for name, game, loader_kind in specifications
    }
    for target in targets.values():
        launcher.save_instance(Instance(target.instance_id, target.game_version))
    monkeypatch.setattr(Launcher, "describe_content_target", lambda _l, name: targets[name])
    monkeypatch.setattr(
        Launcher,
        "fetch_versions",
        lambda *_args: (
            replace(release("new-beta", "1.20.1", "fabric"), version_type="beta"),
            release("stable", "1.20.1", "fabric"),
            release("old", "1.20.1", "fabric"),
            release("forge", "1.21.1", "forge"),
            release("neoforge", "1.21.1", "neoforge"),
            replace(release("only-beta", "1.18.2", "fabric"), version_type="beta"),
        ),
    )
    bridge.announce_instances_changed()
    root_item.setProperty("currentIndex", 2)
    library = find_control(root_item, "minimalLibrary")
    library.setProperty("kind", "mod")
    library.refresh()
    content = view.rootContext().contextProperty("contentBridge")
    wait_until(lambda: not content.searching and bool(content.results))
    project = view.rootContext().contextProperty("projectBridge")
    project.openProject("demo")
    wait_until(lambda: not project.details["loading"])
    picker = find_control(root_item, "projectVersionPicker")
    assert not picker.property("instanceId") and not picker.property("versionId")
    return picker, project, calls


def choose_target(context: Preview, picker: Any, instance_id: str) -> None:
    _launcher, _view, _bridge, root_item = context
    index = next(
        index
        for index, row in enumerate(picker.property("targets").toVariant())
        if row["instanceId"] == instance_id
    )
    find_control(root_item, "projectTarget").choose(index + 1, False)
    wait_until(lambda: picker.property("instanceId") == instance_id)
    QTest.qWait(20)


@pytest.mark.parametrize(
    "instance_id,version_id,game_version",
    [
        ("selected", "stable", "1.20.1"),
        ("quilt", "stable", "1.20.1"),
        ("forge", "forge", "1.21.1"),
        ("neoforge", "neoforge", "1.21.1"),
        ("beta-only", "only-beta", "1.18.2"),
    ],
)
def test_instance_alone_selects_compatible_release_and_installs_it(
    preview: Preview,
    monkeypatch: pytest.MonkeyPatch,
    instance_id: str,
    version_id: str,
    game_version: str,
) -> None:
    picker, project, calls = configure(preview, monkeypatch)
    _launcher, view, _bridge, root_item = preview
    choose_target(preview, picker, instance_id)
    wait_until(lambda: picker.property("canInstall"))
    assert picker.property("versionId") == version_id
    assert picker.property("gameVersion") == game_version
    assert not find_control(root_item, "projectRelease").isVisible()
    press(view, find_control(root_item, "projectInstall"))
    wait_until(lambda: bool(calls) and not project.installing)
    assert len(calls) == 1
    assert (calls[0].instance_id, calls[0].version_id) == (instance_id, version_id)


def test_manual_choice_survives_refresh_but_switching_target_restores_recommendation(
    preview: Preview,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    picker, project, calls = configure(preview, monkeypatch)
    _launcher, view, _bridge, root_item = preview
    choose_target(preview, picker, "selected")
    press(view, find_control(root_item, "projectChangeVersion"))
    select = find_control(root_item, "projectRelease")
    select.forceActiveFocus()
    QTest.keyClick(view, Qt.Key.Key_Down)
    assert picker.property("versionId") == "old"
    project.refreshTargets()
    project.failed.emit("Temporary download failure")
    QTest.qWait(40)
    assert picker.property("versionId") == "old" and picker.property("versionExpanded")
    assert find_control(root_item, "projectUseRecommended").isVisible()
    press(view, find_control(root_item, "projectUseRecommended"))
    assert picker.property("versionId") == "stable"
    assert not find_control(root_item, "projectUseRecommended").isVisible()
    select.forceActiveFocus()
    QTest.keyClick(view, Qt.Key.Key_Up)
    assert picker.property("versionId") == "new-beta"
    project.refreshTargets()
    QTest.qWait(20)
    assert picker.property("versionId") == "new-beta"
    choose_target(preview, picker, "forge")
    assert picker.property("versionId") == "forge" and not picker.property("versionExpanded")
    choose_target(preview, picker, "selected")
    assert picker.property("versionId") == "stable"
    assert not calls


@pytest.mark.parametrize("instance_id", ["vanilla", "unsupported"])
def test_incompatible_instance_blocks_install_then_recovers_when_target_changes(
    preview: Preview,
    monkeypatch: pytest.MonkeyPatch,
    instance_id: str,
) -> None:
    picker, _project, calls = configure(preview, monkeypatch)
    _launcher, view, _bridge, root_item = preview
    choose_target(preview, picker, "selected")
    choose_target(preview, picker, instance_id)
    assert picker.property("gameVersion") == ("1.20.1" if instance_id == "vanilla" else "1.19.4")
    assert not picker.property("versionId") and not picker.property("canInstall")
    button = find_control(root_item, "projectInstall")
    assert not button.property("clickable")
    assert "Không có bản phát hành phù hợp" in button.property("disabledReason")
    press(view, button)
    assert not calls
    choose_target(preview, picker, "neoforge")
    assert picker.property("canInstall") and picker.property("versionId") == "neoforge"


def test_removed_target_and_reopened_popup_do_not_keep_old_install_choice(
    preview: Preview,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    picker, project, calls = configure(preview, monkeypatch)
    _launcher, view, _bridge, root_item = preview
    choose_target(preview, picker, "selected")
    monkeypatch.setattr(Launcher, "list_instances", lambda _l: ())
    project.refreshTargets()
    wait_until(lambda: not picker.property("instanceId"))
    assert not picker.property("versionId") and not picker.property("canInstall")
    assert find_control(root_item, "projectCreateCompatible").isVisible()
    press(view, find_control(root_item, "projectClose"))
    project.openProject("demo")
    wait_until(lambda: not project.details["loading"])
    assert not picker.property("instanceId") and not picker.property("versionExpanded")
    assert not calls


@pytest.mark.parametrize("language", ["vi", "en"])
def test_menu_and_locale_changes_keep_visible_target_and_release_in_sync(
    preview: Preview,
    monkeypatch: pytest.MonkeyPatch,
    language: str,
) -> None:
    picker, project, _calls = configure(preview, monkeypatch)
    _launcher, view, _bridge, root_item = preview
    choose_target(preview, picker, "selected")
    target = find_control(root_item, "projectTarget")
    press(view, find_control(root_item, "projectChangeVersion"))
    select = find_control(root_item, "projectRelease")
    select.choose(2, False)
    assert picker.property("versionId") == "old"
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        150, False, False, True, language
    )
    project.refreshTargets()
    QTest.qWait(60)
    assert target.property("displayText").startswith("selected  ·  ")
    assert "1.20.1" in target.property("displayText")
    assert target.property("currentText") == target.property("displayText")
    assert "old" in select.property("displayText")
    assert select.property("currentIndex") == 2
    press(view, find_control(root_item, "projectUseRecommended"))
    wait_until(lambda: select.property("currentIndex") == 1)
    assert "stable" in select.property("displayText")
    assert not find_control(root_item, "projectUseRecommended").isVisible()
