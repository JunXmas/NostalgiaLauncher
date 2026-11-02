"""Tải vào vùng tạm, kiểm lại toàn bộ mod, tráo thư mục và giữ bản trước để hoàn tác."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from nostalgia.errors import ContentError
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.model import ModScan
from nostalgia.modcheck.scan import build_scan
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairGateway, RepairPlan
from nostalgia.modrepair.staging import disable_archive
from nostalgia.modrepair.verification import remaining_findings
from nostalgia.net.http import HttpClient
from nostalgia.storage.directory_swap import (
    commit_directory,
    latest_directory_change,
    stage_directory,
    tree_fingerprint,
    undo_directory,
)
from nostalgia.storage.directory_swap import tree_hash as tree_hash
from nostalgia.storage.files import resolve_child


@contextmanager
def lock_mods(game_dir: Path) -> Iterator[None]:
    game_dir.mkdir(parents=True, exist_ok=True)
    path = game_dir / ".nostalgia-mods.lock"
    if path.is_symlink():
        raise ContentError("Khóa mod không được là symlink.")
    with path.open("a+b") as stream:
        try:
            if os.name == "nt":
                import importlib

                msvcrt = importlib.import_module("msvcrt")

                stream.seek(0)
                stream.write(b"0")
                stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ContentError("Một tác vụ khác đang sửa mod.") from error
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def apply_plan(
    game_dir: Path,
    scan: ModScan,
    plan: RepairPlan,
    gateway: RepairGateway,
    http_client: HttpClient,
    is_running: Callable[[], bool],
) -> str:
    if not plan.changes or plan.unresolved or scan_hash(scan) != plan.scan_hash:
        raise ContentError("Phương án còn điểm chưa xác minh; chưa áp dụng.")
    with lock_mods(game_dir):
        if is_running():
            raise ContentError("Tắt Minecraft trước khi sửa mod.")
        directory = game_dir / "mods"
        if directory.is_symlink():
            raise ContentError("Không sửa mods là symlink.")
        original = tree_fingerprint(directory)
        current = build_scan(
            scan_archives(game_dir, scan.loader_kind),
            scan.game_version,
            scan.loader_kind,
            scan.loader_version,
            scan.java_major,
        )
        current = with_game_logs(current, game_dir)
        if scan_hash(current) != plan.scan_hash:
            raise ContentError("Bộ mod đã thay đổi; hãy quét lại.")
        with tempfile.TemporaryDirectory(prefix=".nostalgia-stage-", dir=game_dir) as temporary:
            stage = Path(temporary)
            stage_directory(directory, stage / "mods")
            for change in plan.changes:
                destination = resolve_child(stage / "mods", change.file_name)
                if change.operation == "disable":
                    disable_archive(destination)
                else:
                    if destination.exists():
                        raise ContentError("Phụ thuộc tải về trùng file đang có.")
                    with destination.open("xb") as stream:

                        def consume(payload: bytes) -> None:
                            stream.write(payload)

                        http_client.stream(change.url, consume, max_bytes=change.size)
                    if destination.stat().st_size != change.size:
                        raise ContentError("Phụ thuộc tải chưa đủ byte.")
                    with destination.open("rb") as hash_stream:
                        if hashlib.file_digest(hash_stream, "sha512").hexdigest() != change.sha512:
                            raise ContentError("Phụ thuộc sai hash SHA-512.")
            repaired = build_scan(
                scan_archives(stage, scan.loader_kind),
                scan.game_version,
                scan.loader_kind,
                scan.loader_version,
                scan.java_major,
            )
            remaining = remaining_findings(scan, repaired, plan)
            if remaining:
                raise ContentError("Kiểm lại vẫn còn lỗi/chưa xác minh: " + remaining[0].reason)
            gateway.authorize(plan)
            if is_running() or tree_fingerprint(directory) != original:
                raise ContentError("Game hoặc bộ mod thay đổi trong lúc chuẩn bị; đã hủy sửa.")
            return commit_directory(
                directory, stage / "mods", game_dir / ".nostalgia-repairs", original
            )


def undo_repair(game_dir: Path, receipt_id: str, is_running: Callable[[], bool]) -> None:
    with lock_mods(game_dir):
        if is_running():
            raise ContentError("Tắt game trước khi hoàn tác.")
        undo_directory(game_dir / "mods", game_dir / ".nostalgia-repairs", receipt_id)


def latest_repair(game_dir: Path) -> str:
    return latest_directory_change(game_dir / ".nostalgia-repairs")
