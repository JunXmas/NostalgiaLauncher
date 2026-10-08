"""Tải vào vùng tạm, kiểm lại toàn bộ mod, tráo thư mục và giữ bản trước để hoàn tác."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from nostalgia.errors import ContentError, NostalgiaError
from nostalgia.modcheck.archive import hash_archive, scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.model import ModScan
from nostalgia.modcheck.scan import build_scan
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairGateway, RepairPlan
from nostalgia.modrepair.staging import disable_archive
from nostalgia.modrepair.verification import remaining_findings
from nostalgia.net.http import HttpClient
from nostalgia.storage.files import atomic_write_json, read_json, resolve_child


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


def tree_hash(directory: Path) -> str:
    if directory.is_symlink():
        raise ContentError("Thư mục mods có symlink; không tự sửa.")
    digest = hashlib.sha256()
    if not directory.exists():
        return digest.hexdigest()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ContentError("Thư mục mods có symlink; không tự sửa.")
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode())
            digest.update(hash_archive(path).encode())
    return digest.hexdigest()


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
        original = tree_hash(directory)
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
            if directory.exists():
                shutil.copytree(directory, stage / "mods")
            else:
                (stage / "mods").mkdir()
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
            if is_running() or tree_hash(directory) != original:
                raise ContentError("Game hoặc bộ mod thay đổi trong lúc chuẩn bị; đã hủy sửa.")
            receipt_id = uuid.uuid4().hex
            history = game_dir / ".nostalgia-repairs"
            if history.is_symlink():
                raise ContentError("Kho hoàn tác là symlink.")
            receipt = history / receipt_id
            receipt.mkdir(parents=True)
            if not directory.exists():
                directory.mkdir()
            after = tree_hash(stage / "mods")
            atomic_write_json(
                receipt / "receipt.json", {"status": "prepared", "after": after, "before": original}
            )
            directory.replace(receipt / "before")
            try:
                (stage / "mods").replace(directory)
                atomic_write_json(
                    receipt / "receipt.json",
                    {"status": "applied", "after": after, "before": original},
                )
            except BaseException:
                if directory.exists():
                    shutil.rmtree(directory)
                (receipt / "before").replace(directory)
                raise
            return receipt_id


def undo_repair(game_dir: Path, receipt_id: str, is_running: Callable[[], bool]) -> None:
    if len(receipt_id) != 32 or any(letter not in "0123456789abcdef" for letter in receipt_id):
        raise ContentError("Mã hoàn tác không hợp lệ.")
    with lock_mods(game_dir):
        if is_running():
            raise ContentError("Tắt game trước khi hoàn tác.")
        receipt = game_dir / ".nostalgia-repairs" / receipt_id
        if receipt.parent.is_symlink() or receipt.is_symlink() or (receipt / "before").is_symlink():
            raise ContentError("Kho hoàn tác không an toàn.")
        if (receipt / "receipt.json").is_symlink():
            raise ContentError("Biên nhận hoàn tác không an toàn.")
        fields = as_mapping(read_json(receipt / "receipt.json"))
        directory = game_dir / "mods"
        if fields.get("status") not in ("applied", "prepared") or tree_hash(
            receipt / "before"
        ) != fields.get("before"):
            raise ContentError("Bản sao lưu không khớp; chưa hoàn tác.")
        if directory.exists() and tree_hash(directory) != fields.get("after"):
            raise ContentError("Mod đã thay đổi sau sửa; không ghi đè thay đổi của bạn.")
        if directory.exists():
            directory.replace(receipt / "after")
        try:
            (receipt / "before").replace(directory)
        except BaseException:
            if (receipt / "after").exists():
                (receipt / "after").replace(directory)
            raise
        atomic_write_json(
            receipt / "receipt.json",
            {"status": "undone", "after": as_string(fields.get("after")) or ""},
        )


def latest_repair(game_dir: Path) -> str:
    history = game_dir / ".nostalgia-repairs"
    if history.is_symlink() or not history.exists():
        return ""
    for receipt in sorted(history.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
        if not receipt.is_dir() or receipt.is_symlink() or len(receipt.name) != 32:
            continue
        if (receipt / "receipt.json").is_file() and not (receipt / "receipt.json").is_symlink():
            try:
                fields = as_mapping(read_json(receipt / "receipt.json"))
            except NostalgiaError:
                continue
            if fields.get("status") in ("applied", "prepared"):
                return receipt.name
    return ""
