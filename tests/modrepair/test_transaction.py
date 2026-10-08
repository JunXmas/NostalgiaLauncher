"""Áp và hoàn tác trên file thật: thay đổi/thu hồi/lỗi tráo thư mục không làm mất mod."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import pytest

from mod_fixture import write_fabric
from nostalgia.errors import ContentError
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.model import ModScan
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairChange, RepairPlan
from nostalgia.modrepair.transaction import apply_plan, latest_repair, tree_hash, undo_repair
from nostalgia.net.http import HttpClient


class RepairFixture:
    def __init__(self, revoked: bool = False) -> None:
        self.revoked = revoked

    def fetch_plan(self, scan: ModScan, selection: str = "") -> RepairPlan:
        del selection
        archive = scan.archives[1]
        return RepairPlan(
            "a" * 64,
            scan_hash(scan),
            int(time.time()) + 900,
            (RepairChange("disable", archive.file_name, archive.sha256, "", 0, "", "Trùng ID"),),
            (),
        )

    def authorize(self, plan: RepairPlan) -> None:
        del plan
        if self.revoked:
            raise ContentError("Phiên bị thu hồi.")


def prepare(game_dir: Path) -> ModScan:
    write_fabric(game_dir / "mods/a.jar", "alpha")
    write_fabric(game_dir / "mods/b.jar", "alpha")
    (game_dir / "saves").mkdir()
    (game_dir / "saves/world.dat").write_bytes(b"world")
    return build_scan(scan_archives(game_dir), "1.20.1", "fabric", "0.16.0", 17)


@pytest.mark.parametrize("existing_disabled", [False, True])
def test_apply_undo_and_persisted_receipt(tmp_path: Path, existing_disabled: bool) -> None:
    scan = prepare(tmp_path)
    if existing_disabled:
        (tmp_path / "mods/b.jar.disabled").write_bytes(b"previous disabled copy")
    before = tree_hash(tmp_path / "mods")
    gateway = RepairFixture()
    receipt = apply_plan(
        tmp_path, scan, gateway.fetch_plan(scan), gateway, HttpClient(), lambda: False
    )
    assert (tmp_path / "mods/b.jar.disabled").is_file() and not (tmp_path / "mods/b.jar").exists()
    if existing_disabled:
        assert (tmp_path / "mods/b.jar.disabled").read_bytes() == b"previous disabled copy"
        assert len(tuple((tmp_path / "mods").glob("b.jar*.disabled"))) == 2
    assert latest_repair(tmp_path) == receipt
    undo_repair(tmp_path, receipt, lambda: False)
    assert (tmp_path / "mods/b.jar").is_file() and (
        tmp_path / "saves/world.dat"
    ).read_bytes() == b"world"
    assert latest_repair(tmp_path) == ""
    assert tree_hash(tmp_path / "mods") == before


@pytest.mark.parametrize("mode", ["changed", "revoked", "running", "unresolved"])
def test_cancel_keeps_original_mods(tmp_path: Path, mode: str) -> None:
    scan = prepare(tmp_path)
    gateway = RepairFixture(mode == "revoked")
    plan = gateway.fetch_plan(scan)
    if mode == "changed":
        write_fabric(tmp_path / "mods/c.jar", "gamma")
    if mode == "unresolved":
        plan = replace(plan, unresolved=("unknown",))
    with pytest.raises(ContentError):
        apply_plan(tmp_path, scan, plan, gateway, HttpClient(), lambda: mode == "running")
    assert (tmp_path / "mods/b.jar").is_file() and not (tmp_path / "mods/b.jar.disabled").exists()


def test_undo_refuses_post_repair_edits(tmp_path: Path) -> None:
    scan = prepare(tmp_path)
    gateway = RepairFixture()
    receipt = apply_plan(
        tmp_path, scan, gateway.fetch_plan(scan), gateway, HttpClient(), lambda: False
    )
    write_fabric(tmp_path / "mods/c.jar", "gamma")
    with pytest.raises(ContentError):
        undo_repair(tmp_path, receipt, lambda: False)
    assert (tmp_path / "mods/c.jar").exists()
