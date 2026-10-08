"""The visible Replace button performs a backed-up replacement and enables real undo."""

import hashlib
import time
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import Preview, find_control, press
from test_minimal_preview import preview as preview

from mod_fixture import write_fabric
from nostalgia.api import Launcher, ModScan, RepairPlan, RepairScan
from nostalgia.instance.model import Instance
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairChange
from nostalgia.net.http import HttpClient
from nostalgia.ui.mod_repair_bridge import ModRepairBridge

pytestmark = pytest.mark.usefixtures("qt_app")


class ProposedRepair:
    def __init__(self, proposal: RepairPlan, changed: bool = False) -> None:
        self.proposal, self.changed, self.authorizations = proposal, changed, 0

    def fetch_plan(self, scan: ModScan, selection: str = "") -> RepairPlan:
        assert scan_hash(scan) == self.proposal.scan_hash
        proposal = replace(self.proposal, partial=bool(selection))
        if selection and self.changed:
            return replace(
                proposal,
                changes=(proposal.changes[0], replace(proposal.changes[1], version_number="3.0.0")),
            )
        return proposal

    def authorize(self, plan: RepairPlan) -> None:
        assert plan.partial and plan.changes == self.proposal.changes
        self.authorizations += 1


@pytest.mark.parametrize("changed", [False, True])
def test_replace_button_downloads_verified_mod_and_can_undo(
    preview: Preview, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: bool
) -> None:
    launcher, view, _bridge, root_item = preview
    launcher.create_instance(Instance("repair", "1.20.1", "Mod repair test"))
    game_dir = launcher.paths.instance_dir("repair")
    write_fabric(game_dir / "mods/alpha.jar", "alpha", depends={"beta": ">=2.0.0"})
    write_fabric(game_dir / "mods/beta-old.jar", "beta")
    (game_dir / "saves").mkdir()
    (game_dir / "saves/world.dat").write_bytes(b"world")
    (game_dir / "logs").mkdir()
    (game_dir / "logs/latest.log").write_text(
        "Mod 'Alpha' (alpha) 1.0.0 requires version 2.0.0 or later of mod 'Beta' (beta), "
        "but only the wrong version is present: 1.0.0!"
    )
    scan = with_game_logs(
        build_scan(scan_archives(game_dir), "1.20.1", "fabric", "0.16.0", 17), game_dir
    )
    monkeypatch.setattr(Launcher, "scan_mod_repair", lambda _self, _id: RepairScan(scan, ""))
    write_fabric(tmp_path / "beta-new.jar", "beta", version="2.1.0")
    payload = (tmp_path / "beta-new.jar").read_bytes()
    old = next(archive for archive in scan.archives if archive.file_name == "beta-old.jar")
    changes = (
        RepairChange(
            "disable", old.file_name, old.sha256, "", 0, "", "Old version", "beta", "1.0.0"
        ),
        RepairChange(
            "add",
            "beta-new.jar",
            "",
            "https://cdn.modrinth.com/data/beta/mod.jar",
            len(payload),
            hashlib.sha512(payload).hexdigest(),
            "Log requires beta >=2",
            "beta",
            "2.1.0",
            "Beta",
        ),
    )
    gateway = ProposedRepair(
        RepairPlan("a" * 64, scan_hash(scan), int(time.time()) + 900, changes, ()), changed
    )

    def deliver(_self: HttpClient, _url: str, consume: object, **_kwargs: object) -> None:
        assert callable(consume)
        consume(payload)

    monkeypatch.setattr(HttpClient, "stream", deliver)
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    QTest.qWait(100)
    repair = view.rootContext().contextProperty("modRepairBridge")
    assert isinstance(repair, ModRepairBridge)
    repair.set_gateway(gateway)
    dialog = find_control(root_item, "modRepairDialog")
    dialog.openFor({"instanceId": "repair", "label": "Mod repair test"})
    wait_until(lambda: repair.details["scanned"] and not repair.busy)
    assert "latest.log" in repair.details["logSources"]
    press(view, find_control(root_item, "modPlan"))
    wait_until(lambda: bool(repair.details["recommendations"]) and not repair.busy)
    card = repair.details["recommendations"][0]
    assert card["currentVersion"] == "1.0.0" and card["version"] == "2.1.0"
    QTest.qWait(80)
    press(view, find_control(root_item, "replaceMod-beta"))
    wait_until(lambda: not repair.busy)
    if changed:
        assert "thay đổi" in repair.details["note"]
        assert not (game_dir / "mods/beta-new.jar").exists()
        assert (game_dir / "mods/beta-old.jar").exists()
        assert gateway.authorizations == 0
    else:
        assert gateway.authorizations == 1 and repair.details["canUndo"]
        assert (game_dir / "mods/beta-new.jar").read_bytes() == payload
        assert (game_dir / "mods/beta-old.jar.disabled").exists()
        press(view, find_control(root_item, "modUndo"))
        wait_until(lambda: not repair.busy and not repair.details["canUndo"])
        assert (game_dir / "mods/beta-old.jar").exists()
        assert not (game_dir / "mods/beta-new.jar").exists()
    assert (game_dir / "saves/world.dat").read_bytes() == b"world"
    dialog.close()
