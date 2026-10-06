"""Sai hash và lỗi tráo thư mục không được thay đổi bản mod đang dùng."""

import hashlib
from pathlib import Path

import pytest
from test_transaction import RepairFixture, prepare

from mod_fixture import write_fabric
from nostalgia.errors import ContentError
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairChange, RepairPlan
from nostalgia.modrepair.transaction import apply_plan, tree_hash
from nostalgia.net.http import HttpClient


@pytest.mark.parametrize("tampered", [False, True])
def test_addition_verified_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tampered: bool
) -> None:
    game_dir = tmp_path / "game"
    write_fabric(game_dir / "mods/a.jar", "alpha", depends={"beta": "*"})
    write_fabric(tmp_path / "beta.jar", "beta")
    payload = (tmp_path / "beta.jar").read_bytes()
    scan = build_scan(scan_archives(game_dir), "1.20.1", "fabric", "0.16.0", 17)
    change = RepairChange(
        "add",
        "beta.jar",
        "",
        "https://cdn.modrinth.com/data/x/beta.jar",
        len(payload),
        hashlib.sha512(payload).hexdigest(),
        "Thêm beta",
    )
    plan = RepairPlan("a" * 64, scan_hash(scan), 9999999999, (change,), ())
    before = tree_hash(game_dir / "mods")

    def deliver_archive(_self: HttpClient, _url: str, consume: object, **_kwargs: object) -> None:
        assert callable(consume)
        consume(b"x" * len(payload) if tampered else payload)

    monkeypatch.setattr(HttpClient, "stream", deliver_archive)
    if tampered:
        with pytest.raises(ContentError, match="hash"):
            apply_plan(game_dir, scan, plan, RepairFixture(), HttpClient(), lambda: False)
        assert tree_hash(game_dir / "mods") == before
    else:
        apply_plan(game_dir, scan, plan, RepairFixture(), HttpClient(), lambda: False)
        assert (game_dir / "mods/beta.jar").read_bytes() == payload


def test_failed_stage_rename_restores_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan = prepare(tmp_path)
    before = tree_hash(tmp_path / "mods")
    replace_path = Path.replace

    def fail_stage(path: Path, target: Path) -> Path:
        if path.parent.name.startswith(".nostalgia-stage-"):
            raise OSError("disk failure")
        return replace_path(path, target)

    monkeypatch.setattr(Path, "replace", fail_stage)
    gateway = RepairFixture()
    with pytest.raises(OSError, match="disk failure"):
        apply_plan(tmp_path, scan, gateway.fetch_plan(scan), gateway, HttpClient(), lambda: False)
    assert tree_hash(tmp_path / "mods") == before
