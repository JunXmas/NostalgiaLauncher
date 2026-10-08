"""Replace fixes only the selected group, revalidates log evidence and preserves other mods."""

import hashlib
import time
from dataclasses import replace
from pathlib import Path

import pytest
from test_transaction import RepairFixture

from mod_fixture import write_fabric
from nostalgia.errors import ContentError
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairChange, RepairPlan
from nostalgia.modrepair.transaction import apply_plan, tree_hash, undo_repair
from nostalgia.net.http import HttpClient
from nostalgia.ui.mod_repair_cards import check_chosen_group, repair_cards


@pytest.mark.parametrize("problem", ["", "wrong_mod", "log_changed", "proposal_changed"])
def test_replace_revalidates_identity_logs_and_selected_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    game_dir = tmp_path / "game"
    write_fabric(game_dir / "mods/alpha.jar", "alpha", depends={"beta": ">=2.0.0", "private": "*"})
    write_fabric(game_dir / "mods/beta-old.jar", "beta")
    (game_dir / "logs").mkdir()
    log = game_dir / "logs/latest.log"
    log.write_text(
        "Mod 'Alpha' (alpha) 1.0.0 requires version 2.0.0 or later of mod 'Beta' (beta), "
        "but only the wrong version is present: 1.0.0!"
    )
    (game_dir / "saves").mkdir()
    (game_dir / "saves/world.dat").write_bytes(b"world")
    scan = with_game_logs(
        build_scan(scan_archives(game_dir), "1.20.1", "fabric", "0.16.0", 17), game_dir
    )
    old = next(archive for archive in scan.archives if archive.file_name == "beta-old.jar")
    write_fabric(
        tmp_path / "candidate.jar", "other" if problem == "wrong_mod" else "beta", version="2.1.0"
    )
    payload = (tmp_path / "candidate.jar").read_bytes()
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
    shown = RepairPlan("a" * 64, scan_hash(scan), int(time.time()) + 900, changes, ("private",))
    fresh = replace(shown, plan_id="b" * 64, unresolved=(), partial=True)
    assert repair_cards(shown, scan)[0]["currentVersion"] == "1.0.0"
    if problem == "proposal_changed":
        fresh = replace(fresh, changes=(changes[0], replace(changes[1], version_number="3.0.0")))
        with pytest.raises(ContentError, match="thay đổi"):
            check_chosen_group(shown, fresh, "beta")
        return
    check_chosen_group(shown, fresh, "beta")
    before = tree_hash(game_dir / "mods")

    def deliver(_self: HttpClient, _url: str, consume: object, **_kwargs: object) -> None:
        assert callable(consume)
        consume(payload)

    monkeypatch.setattr(HttpClient, "stream", deliver)
    if problem == "log_changed":
        log.write_text(log.read_text().replace("2.0.0 or later", "3.0.0 or later"))
    if problem:
        with pytest.raises(ContentError):
            apply_plan(game_dir, scan, fresh, RepairFixture(), HttpClient(), lambda: False)
        assert tree_hash(game_dir / "mods") == before
    else:
        receipt = apply_plan(game_dir, scan, fresh, RepairFixture(), HttpClient(), lambda: False)
        repaired = build_scan(scan_archives(game_dir), "1.20.1", "fabric", "0.16.0", 17)
        assert {finding.mod_id for finding in repaired.findings} == {"private"}
        assert (game_dir / "mods/beta-old.jar.disabled").exists()
        assert (game_dir / "saves/world.dat").read_bytes() == b"world"
        undo_repair(game_dir, receipt, lambda: False)
        assert tree_hash(game_dir / "mods") == before


def test_blocked_group_cannot_be_presented_as_ready(tmp_path: Path) -> None:
    write_fabric(tmp_path / "mods/alpha.jar", "alpha")
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    change = RepairChange(
        "add", "beta.jar", "", "", 100, "c" * 128, "Needs unresolved Gamma", "beta", "2.0.0"
    )
    proposal = RepairPlan(
        "a" * 64,
        scan_hash(scan),
        int(time.time()) + 900,
        (change,),
        ("gamma",),
        blocked_groups=("beta",),
    )
    assert not repair_cards(proposal, scan)[0]["canReplace"]
