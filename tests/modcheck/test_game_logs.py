"""Dependency evidence stays local, bounded, current, and distinct from uncertain crashes."""

import json
import os
import time
from pathlib import Path

import pytest

from mod_fixture import write_fabric
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.log_patterns import parse_log
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import scan_payload

FABRIC_FAILURE = (
    "Mod 'Alpha' (alpha) 1.0.0 requires version 2.0.0 or later of mod 'Beta' (beta), "
    "but only the wrong version is present: 1.0.0!"
)


@pytest.mark.parametrize(
    "line,dependency,predicate",
    [
        (FABRIC_FAILURE, "beta", ">=2.0.0"),
        (
            "Mod 'Alpha' (alpha) 1.0.0 requires any version of mod 'Beta' (beta), "
            "which is missing!",
            "beta",
            "*",
        ),
        (
            "Mod ID: 'beta', Requested by: 'alpha', Expected range: '[2.0.0,3.0.0)', "
            "Actual version: '[MISSING]'",
            "beta",
            "maven:[2.0.0,3.0.0)",
        ),
        ("Mod alpha requires beta 2.0.0 or above\n    Currently, beta is 1.0.0", "beta", ">=2.0.0"),
    ],
)
def test_explicit_loader_dependency_formats(line: str, dependency: str, predicate: str) -> None:
    diagnostics = parse_log(line, "latest.log")
    assert len(diagnostics) == 1
    assert diagnostics[0].mod_id == "alpha"
    assert diagnostics[0].dependency_id == dependency
    assert diagnostics[0].predicates == (predicate,)


def test_log_constraints_ignore_satisfied_dependencies_and_stale_mod_version(
    tmp_path: Path,
) -> None:
    write_fabric(tmp_path / "mods/alpha.jar", "alpha")
    write_fabric(tmp_path / "mods/beta.jar", "beta")
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    logs = tmp_path / "logs"
    logs.mkdir()
    path = logs / "latest.log"
    path.write_text(FABRIC_FAILURE + "\nAccessToken: private-token /home/private-user/server-ip")
    diagnosed = with_game_logs(scan, tmp_path)
    assert len(diagnosed.diagnostics) == 1
    payload = scan_payload(diagnosed).decode()
    assert "private-token" not in payload and "/home/" not in payload and "server-ip" not in payload
    assert json.loads(payload)["diagnostics"][0]["predicates"] == [">=2.0.0"]
    path.write_text(FABRIC_FAILURE.replace("1.0.0 requires", "0.9.0 requires"))
    assert not with_game_logs(scan, tmp_path).diagnostics
    path.write_text(FABRIC_FAILURE.replace("2.0.0 or later", "1.0.0 or later"))
    assert not with_game_logs(scan, tmp_path).diagnostics


def test_old_crash_reports_and_symlinks_are_ignored(tmp_path: Path) -> None:
    write_fabric(tmp_path / "mods/alpha.jar", "alpha")
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    (tmp_path / "logs").mkdir()
    (tmp_path / "crash-reports").mkdir()
    latest = tmp_path / "logs/latest.log"
    latest.write_text("Game successfully started")
    crash = tmp_path / "crash-reports/crash-old.txt"
    crash.write_text(FABRIC_FAILURE)
    os.utime(crash, (time.time() - 3600, time.time() - 3600))
    assert not with_game_logs(scan, tmp_path).diagnostics
    secret = tmp_path / "private.txt"
    secret.write_text(FABRIC_FAILURE)
    try:
        (tmp_path / "logs/debug.log").symlink_to(secret)
    except OSError:
        pytest.skip("Symlink requires permission on this platform")
    assert not with_game_logs(scan, tmp_path).diagnostics


def test_runtime_fault_is_reported_without_a_guessed_version(tmp_path: Path) -> None:
    write_fabric(tmp_path / "mods/alpha.jar", "alpha")
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs/latest.log").write_text("Mixin apply for mod alpha failed at injected method")
    diagnosed = with_game_logs(scan, tmp_path)
    assert diagnosed.diagnostics[0].code == "runtime"
    assert "chưa đủ dữ liệu" in diagnosed.findings[0].reason


def test_log_tail_is_bounded_and_deduplicated() -> None:
    assert len(parse_log((FABRIC_FAILURE + "\n") * 20000, "latest.log")) == 1
    assert not parse_log(FABRIC_FAILURE + "\n" + "x" * 2097152, "latest.log")


def test_crash_from_previous_attempt_is_not_reused_after_newer_log(tmp_path: Path) -> None:
    write_fabric(tmp_path / "mods/alpha.jar", "alpha")
    scan = build_scan(scan_archives(tmp_path), "1.20.1", "fabric", "0.16.0", 17)
    (tmp_path / "logs").mkdir()
    (tmp_path / "crash-reports").mkdir()
    latest = tmp_path / "logs/latest.log"
    latest.write_text("Game successfully started")
    crash = tmp_path / "crash-reports/crash-previous.txt"
    crash.write_text(FABRIC_FAILURE)
    os.utime(crash, (time.time() - 10, time.time() - 10))
    assert not with_game_logs(scan, tmp_path).diagnostics
