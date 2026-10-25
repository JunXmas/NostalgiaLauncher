"""Sửa tại chỗ: lỗi log thật trên máy chủ dự án đổi thành hành động launcher tự làm."""

from __future__ import annotations

from pathlib import Path

from mod_fixture import write_fabric
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.local_fix import pick_loader_version, suggest_local_fixes
from nostalgia.modcheck.model import ModScan
from nostalgia.modcheck.scan import build_scan

# Trích nguyên văn (bỏ đường dẫn) từ latest.log của bản chơi "foreverworld" trên máy jun.
LOADER_TOO_OLD = (
    "[main/INFO]: Loading Minecraft 1.21.11 with Fabric Loader 0.19.3\n"
    "[main/ERROR]: Incompatible mods found!\n"
    "net.fabricmc.loader.impl.FormattedException: Some of your mods are incompatible with the "
    "game or each other!\n"
    "A potential solution has been determined, this may resolve your problem:\n"
    "\t - Replace 'Fabric Loader' (fabricloader) 0.19.3 with version 0.19.5 or later.\n"
    "More details:\n"
    "\t - Mod 'Cinematic' (cinematic) 2.1.0 requires version 0.19.5 or later of mod 'Fabric "
    "Loader' (fabricloader), but only the wrong version is present: 0.19.3!\n"
)
MIXIN_CRASH = "[main/ERROR]: Mixin apply for mod brokenmod failed brokenmod.mixins.json:Foo\n"


def scan_with_log(tmp_path: Path, log: str) -> ModScan:
    loader_needed = {"fabricloader": ">=0.19.5"}
    write_fabric(tmp_path / "mods/cine.jar", "cinematic", version="2.1.0", depends=loader_needed)
    write_fabric(tmp_path / "mods/broken.jar", "brokenmod")
    (tmp_path / "mods/rotten.jar").write_bytes(b"not a zip")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs/latest.log").write_text(log)
    scan = build_scan(scan_archives(tmp_path), "1.21.11", "fabric", "0.19.3", 21)
    return with_game_logs(scan, tmp_path)


def test_old_loader_becomes_a_loader_upgrade_and_bad_jars_are_disabled(tmp_path: Path) -> None:
    fixes = suggest_local_fixes(scan_with_log(tmp_path, LOADER_TOO_OLD + MIXIN_CRASH))
    kinds = {(fix.fix_kind, fix.target) for fix in fixes}
    assert ("loader", ">=0.19.5") in kinds
    assert ("disable", "broken.jar") in kinds, "mixin crash chỉ đích danh mod → tắt đúng jar đó"
    assert ("disable", "rotten.jar") in kinds, "jar hỏng không đọc được → tắt"
    assert not any(fix.fix_kind == "dependency" and fix.target == "fabricloader" for fix in fixes)


def test_tab_inside_metadata_string_is_not_a_broken_jar(tmp_path: Path) -> None:
    """BetterGrassify thật có tab thô trong fabric.mod.json; Fabric Loader nạp bình thường,
    nên không được báo hỏng hay đề nghị tắt."""
    import zipfile

    (tmp_path / "mods").mkdir()
    with zipfile.ZipFile(tmp_path / "mods/grass.jar", "w") as archive:
        archive.writestr(
            "fabric.mod.json",
            '{"id": "bettergrass", "version": "1.8.7",\n "description": "Better\tgrass"}',
        )
    scan = build_scan(scan_archives(tmp_path), "1.21.11", "fabric", "0.19.3", 21)
    assert not scan.archives[0].problem
    assert not suggest_local_fixes(scan)


def test_pick_loader_version_takes_newest_that_satisfies() -> None:
    available = ("0.20.1", "0.19.5", "0.19.3")
    assert pick_loader_version(available, ">=0.19.5") == "0.20.1"
    assert pick_loader_version(available, ">=0.19.5 <0.20") == "0.19.5"
    assert pick_loader_version(available, ">=9") == ""
