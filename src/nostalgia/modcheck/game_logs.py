"""Read bounded local game logs; upload only structured dependency evidence."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import replace
from pathlib import Path

from nostalgia.modcheck.log_patterns import parse_log
from nostalgia.modcheck.model import ModFinding, ModScan
from nostalgia.modcheck.predicate import matches_any


def recent_logs(game_dir: Path) -> tuple[tuple[Path, str], ...]:
    paths: list[tuple[Path, str]] = []
    logs = game_dir / "logs"
    if not logs.is_symlink():
        for name in ("latest.log", "debug.log"):
            path = logs / name
            if not path.is_symlink() and path.is_file():
                paths.append((path, name))
    latest = next((p for p, name in paths if name == "latest.log"), None)
    if latest:
        paths = [
            (p, name) for p, name in paths if p.stat().st_mtime >= latest.stat().st_mtime - 120
        ]
    reports = game_dir / "crash-reports"
    if reports.is_dir() and not reports.is_symlink():
        candidates = [p for p in reports.glob("crash-*.txt") if not p.is_symlink() and p.is_file()]
        newest = max(candidates, key=lambda p: p.stat().st_mtime, default=None)
        if newest and (not latest or newest.stat().st_mtime >= latest.stat().st_mtime - 120):
            paths.append((newest, "crash-report"))
    return tuple(paths)


def with_game_logs(scan: ModScan, game_dir: Path) -> ModScan:
    owners = {
        m.mod_id: (a.file_name, m.version_number) for a in scan.archives for m in a.descriptors
    }
    versions = {mod_id: owner[1] for mod_id, owner in owners.items()}
    versions.update(minecraft=scan.game_version, java=str(scan.java_major))
    versions[
        "fabricloader"
        if scan.loader_kind == "fabric"
        else "quilt_loader"
        if scan.loader_kind == "quilt"
        else scan.loader_kind
    ] = scan.loader_version
    diagnostics = []
    for path, source in recent_logs(game_dir):
        try:
            with path.open("rb") as stream:
                information = os.fstat(stream.fileno())
                if not stat.S_ISREG(information.st_mode):
                    continue
                header = stream.read(32768).decode("utf-8", errors="replace")
                if information.st_size > 2097152:
                    stream.seek(information.st_size - 2097152)
                text = header + "\n" + stream.read(2097152).decode("utf-8", errors="replace")
        except OSError:
            continue
        versions_in_log = re.findall(
            r"(?:Loading Minecraft |Minecraft Version(?: ID)?: |--fml\.mcVersion[, ]+)"
            r"([a-zA-Z0-9_.-]{1,64})",
            text,
        )
        if versions_in_log and scan.game_version not in versions_in_log:
            continue
        for diagnostic in parse_log(text, source):
            owner = owners.get(diagnostic.mod_id)
            if not owner or (
                diagnostic.reported_version and diagnostic.reported_version != owner[1]
            ):
                continue
            present = versions.get(diagnostic.dependency_id)
            if (
                present
                and diagnostic.predicates
                and matches_any(present, diagnostic.predicates) is True
            ):
                continue
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)
    findings = tuple(
        ModFinding(
            "log_dependency",
            owners[d.mod_id][0],
            d.dependency_id,
            (
                "Log "
                + d.source
                + ": lỗi runtime/mixin của "
                + d.mod_id
                + "; chưa đủ dữ liệu để chọn bản thay thế."
            )
            if d.code == "runtime"
            else "Log "
            + d.source
            + ": "
            + d.mod_id
            + " cần "
            + d.dependency_id
            + " "
            + (" | ".join(d.predicates) or "khoảng phiên bản chưa hỗ trợ"),
        )
        for d in diagnostics[:100]
    )
    return replace(scan, findings=scan.findings + findings, diagnostics=tuple(diagnostics[:100]))
