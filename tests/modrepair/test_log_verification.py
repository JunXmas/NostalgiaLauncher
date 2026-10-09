"""A confirmed log repair need not rewrite mods with unrelated metadata warnings."""

import time
from dataclasses import replace
from pathlib import Path

from mod_fixture import write_fabric
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairChange, RepairPlan
from nostalgia.modrepair.verification import remaining_findings


def test_full_log_repair_keeps_old_warning_but_blocks_new_dependency_failure(
    tmp_path: Path,
) -> None:
    write_fabric(tmp_path / "mods/alpha.jar", "alpha", depends={"beta": ">=2"})
    write_fabric(tmp_path / "mods/private.jar", "private", depends={"custom": "*"})
    write_fabric(tmp_path / "mods/beta.jar", "beta")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs/latest.log").write_text(
        "Mod 'Alpha' (alpha) 1.0.0 requires version 2.0.0 or later of mod 'Beta' (beta), "
        "but only the wrong version is present: 1.0.0!"
    )
    scan = with_game_logs(
        build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17), tmp_path
    )
    plan = RepairPlan(
        "a" * 64,
        scan_hash(scan),
        int(time.time()) + 900,
        (RepairChange("add", "beta.jar", "", "", 1, "", "Log requires beta >=2", "beta"),),
        (),
    )
    write_fabric(tmp_path / "mods/beta.jar", "beta", version="2.1.0")
    repaired = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    assert repaired.findings and not remaining_findings(scan, repaired, plan)
    # An old metadata-only full plan retains its strict verification contract.
    assert remaining_findings(replace(scan, diagnostics=()), repaired, plan)
    write_fabric(tmp_path / "mods/beta.jar", "beta", version="2.1.0", depends={"new_missing": "*"})
    repaired = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    remaining = remaining_findings(scan, repaired, plan)
    assert {finding.mod_id for finding in remaining} == {"new_missing"}
