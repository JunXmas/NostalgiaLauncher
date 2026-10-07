"""Native full draft access and production isolation, including the test tools overlay."""

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from nostalgia_draft.runtime import build_review_view
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until

from nostalgia.api import Instance, Launcher
from nostalgia.launch.runner import InstallReport
from nostalgia.ui.runtime import build_release_view
from nostalgia.ui.worker import wait_for_background
from nostalgia.version.meta import VersionMeta
from qt_controls import find_control, press


@pytest.mark.usefixtures("qt_app")
def test_draft_opens_ultimate_tools_and_standard_release_stays_locked(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    warnings: list[str] = []
    previous = qInstallMessageHandler(lambda _mode, _context, message: warnings.append(message))
    view = build_review_view(launcher)
    try:
        view.show()
        root_item = view.rootObject()
        assert root_item is not None and not view.errors()
        root_item.setProperty("sessionSkipped", True)
        for page in range(7):
            root_item.setProperty("currentIndex", page)
            QTest.qWait(40)
        root_item.setProperty("currentIndex", 0)
        assert view.rootContext().contextProperty("plusFeaturesEnabled") is True
        social = view.rootContext().contextProperty("socialBridge")
        servers = view.rootContext().contextProperty("serverBridge")
        wait_until(
            lambda: bool(social.property("signedIn")) and bool(servers.property("hasAccess"))
        )
        assert social.property("account")["cosmeticPlus"]
        press(view, find_control(root_item, "draftToolsOpen"))
        modal = find_control(root_item, "draftToolsDialog")
        wait_until(lambda: bool(modal.property("opened")))
        press(view, find_item(modal.property("contentItem"), "draftPlan-plus-month-v1"))
        wait_until(lambda: social.property("account").get("planName") == "Plus")
        wait_until(lambda: not bool(servers.property("hasAccess")))
        view.resize(1024, 600)
        QTest.qWait(100)
        assert modal.property("width") < view.width()
        modal.close()
        press(view, find_control(root_item, "draftToolsOpen"))
        press(view, find_item(modal.property("contentItem"), "draftPlan-plus-lifetime-v1"))
        wait_until(lambda: bool(servers.property("hasAccess")))
        modal.close()
        press(view, find_control(root_item, "openSupport"))
        payments = view.rootContext().contextProperty("paymentBridge")
        wait_until(lambda: payments.property("details")["available"] and not payments.busy)
        press(view, find_control(root_item, "paymentCreate"))
        wait_until(lambda: payments.property("details")["stage"] == "pending" and not payments.busy)
        press(view, find_control(root_item, "paymentCheck"))
        wait_until(lambda: not payments.busy)
        assert payments.property("details")["stage"] == "pending"
        press(view, find_control(root_item, "draftPaymentSimulate"))
        wait_until(lambda: payments.property("details")["stage"] == "paid")
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
    view = build_release_view(launcher)
    try:
        assert view.rootContext().contextProperty("plusFeaturesEnabled") is False
        assert not view.rootContext().contextProperty("draftReviewController")
        assert not view.rootContext().contextProperty("draftReviewPanel")
        assert (
            view.rootContext().contextProperty("paymentBridge").property("details")["stage"]
            == "unavailable"
        )
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(previous)
    assert not warnings


@pytest.mark.usefixtures("qt_app")
def test_draft_sync_selector_creates_a_new_instance_through_real_ui(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    source = Instance("own-pack", "1.20.1", "Host pack")
    launcher.create_instance(source)
    metadata = launcher.paths.version_json(source.version_id)
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({"id": "1.20.1", "mainClass": "main"}))
    mods = launcher.instance_game_dir(source) / "mods"
    mods.mkdir()
    (mods / "a.jar").write_bytes(b"host mod")
    view = build_review_view(launcher)
    try:
        view.show()
        root_item = view.rootObject()
        assert root_item is not None
        root_item.setProperty("sessionSkipped", True)
        press(view, find_control(root_item, "draftToolsOpen"))
        modal = find_control(root_item, "draftToolsDialog")
        wait_until(lambda: bool(modal.property("opened")))
        assert find_control(root_item, "draftSyncSource").property("currentIndex") == 0
        report = InstallReport(VersionMeta("1.20.1", "main"), tmp_path / "java", 0, 0, 0)
        with patch.object(Launcher, "install_loader", return_value=report):
            press(view, find_control(root_item, "draftSyncLocal"))
            wait_until(lambda: len(launcher.list_instances()) == 2)
            controller = view.rootContext().contextProperty("draftReviewController")
            wait_until(lambda: not controller.busy)
        copied = next(i for i in launcher.list_instances() if i.instance_id != source.instance_id)
        assert (launcher.instance_game_dir(copied) / "mods/a.jar").read_bytes() == b"host mod"
        assert (mods / "a.jar").read_bytes() == b"host mod"
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
