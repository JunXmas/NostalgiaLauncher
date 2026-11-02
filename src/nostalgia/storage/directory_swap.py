"""Tráo thư mục đã chuẩn bị, giữ bản trước và chỉ hoàn tác khi dữ liệu còn khớp."""

import hashlib
import logging
import os
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path

from nostalgia.errors import ContentError, NostalgiaError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, read_json

logger = logging.getLogger(__name__)


def tree_hash(directory: Path, *, ignored_names: frozenset[str] = frozenset()) -> str:
    if directory.is_symlink():
        raise ContentError("Thư mục nội dung có symlink; không tự thay thế.")
    digest = hashlib.sha256()
    if not directory.exists():
        return digest.hexdigest()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ContentError("Thư mục nội dung có symlink; không tự thay thế.")
        if path.parent == directory and path.name in ignored_names:
            continue
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode())
            with path.open("rb") as stream:
                digest.update(hashlib.file_digest(stream, "sha256").hexdigest().encode())
    return digest.hexdigest()


def tree_fingerprint(directory: Path, *, ignored_names: frozenset[str] = frozenset()) -> str:
    """Dấu thay đổi chỉ từ đường dẫn + cỡ + mtime_ns: không đọc byte nào, O(số file).

    Đủ để phát hiện "có ai đụng vào thư mục trong lúc chuẩn bị/sau khi đổi". Không chống
    giả mạo có chủ đích (đó là máy của chính người chơi).
    """
    if directory.is_symlink():
        raise ContentError("Thư mục nội dung có symlink; không tự thay thế.")
    digest = hashlib.sha256()
    if not directory.exists():
        return digest.hexdigest()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ContentError("Thư mục nội dung có symlink; không tự thay thế.")
        if path.parent == directory and path.name in ignored_names:
            continue
        if path.is_file():
            stat = path.stat()
            digest.update(
                f"{path.relative_to(directory).as_posix()}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode()
            )
    return digest.hexdigest()


def stage_directory(directory: Path, stage: Path) -> None:
    """Dựng vùng tạm bằng hardlink: không chép byte nào, chỉ tạo mục thư mục.

    Điều kiện an toàn: thao tác trên vùng tạm chỉ được thêm file mới, đổi tên hoặc xoá —
    KHÔNG được mở file có sẵn để ghi đè tại chỗ, vì file hardlink dùng chung dữ liệu với bản
    gốc. Mọi đường ghi hiện có (tải về `mkstemp`+replace, `atomic_write_json`, rename khi tắt
    mod) đều tạo inode mới nên thoả. Ổ không hỗ trợ hardlink (FAT/exFAT, vài ổ mạng) thì chép.
    """
    if not directory.exists():
        stage.mkdir()
        return
    try:
        shutil.copytree(directory, stage, copy_function=os.link)
    except OSError:
        shutil.rmtree(stage, ignore_errors=True)
        shutil.copytree(directory, stage)


def _measure(fields: dict[str, JsonValue]) -> Callable[..., str]:
    # Biên nhận cũ (trước format 2) lưu hash nội dung; giữ đọc được để hoàn tác bản sửa cũ.
    return tree_fingerprint if fields.get("format") == FINGERPRINT_FORMAT else tree_hash


FINGERPRINT_FORMAT = 2


def commit_directory(
    directory: Path,
    stage: Path,
    history: Path,
    original: str,
    *,
    ignored_names: frozenset[str] = frozenset(),
) -> str:
    if history.is_symlink() or tree_fingerprint(directory) != original:
        raise ContentError("Nội dung đã thay đổi trong lúc chuẩn bị; không ghi đè.")
    receipt_id = uuid.uuid4().hex
    receipt = history / receipt_id
    receipt.mkdir(parents=True)
    directory.mkdir(exist_ok=True)
    after = tree_fingerprint(stage, ignored_names=ignored_names)
    ignored: dict[str, JsonValue] = {"format": FINGERPRINT_FORMAT}
    if ignored_names:
        ignored["ignored_names"] = list[JsonValue](sorted(ignored_names))
    atomic_write_json(
        receipt / "receipt.json",
        {"status": "prepared", "after": after, "before": original, **ignored},
    )
    directory.replace(receipt / "before")
    try:
        stage.replace(directory)
        atomic_write_json(
            receipt / "receipt.json",
            {"status": "applied", "after": after, "before": original, **ignored},
        )
    except BaseException:
        if directory.exists():
            shutil.rmtree(directory)
        (receipt / "before").replace(directory)
        raise
    _prune(history, keep=KEEP_RECEIPTS)
    return receipt_id


# Mỗi biên nhận giữ nguyên bản cũ của cả thư mục; hardlink nên rẻ khi file chung với bản
# hiện tại, nhưng mod đã bị thay thì vẫn chiếm chỗ. Giữ vài lần gần nhất là đủ để hoàn tác.
KEEP_RECEIPTS = 3


def _prune(history: Path, *, keep: int) -> None:
    receipts = sorted(
        (r for r in history.iterdir() if r.is_dir() and not r.is_symlink() and len(r.name) == 32),
        key=lambda r: r.stat().st_mtime,
        reverse=True,
    )
    for stale in receipts[keep:]:
        shutil.rmtree(stale, ignore_errors=True)


def recover_directory(directory: Path, history: Path) -> bool:
    """Máy tắt/tiến trình chết giữa hai lần đổi tên trong `commit_directory`: thư mục đã sang
    `before` mà bản mới chưa vào chỗ. Đưa `before` về nếu thư mục vẫn trống — kể cả khi game
    đã kịp tạo một thư mục rỗng. Trả True nếu đã khôi phục."""
    if history.is_symlink() or not history.is_dir() or directory.is_symlink():
        return False
    if directory.exists() and any(directory.iterdir()):
        return False
    for receipt in history.iterdir():
        before = receipt / "before"
        if receipt.is_symlink() or before.is_symlink() or not before.is_dir():
            continue
        try:
            fields = as_mapping(read_json(receipt / "receipt.json"))
        except NostalgiaError:
            continue
        if fields.get("status") != "prepared":
            continue
        if directory.exists():
            directory.rmdir()
        before.replace(directory)
        atomic_write_json(receipt / "receipt.json", {**fields, "status": "recovered"})
        logger.warning("Khôi phục %s sau lần đổi bị gián đoạn (%s)", directory, receipt.name)
        return True
    return False


def undo_directory(
    directory: Path,
    history: Path,
    receipt_id: str,
    *,
    ignored_names: frozenset[str] = frozenset(),
) -> None:
    if len(receipt_id) != 32 or any(letter not in "0123456789abcdef" for letter in receipt_id):
        raise ContentError("Mã hoàn tác không hợp lệ.")
    receipt = history / receipt_id
    if history.is_symlink() or receipt.is_symlink() or (receipt / "before").is_symlink():
        raise ContentError("Kho hoàn tác không an toàn.")
    if (receipt / "receipt.json").is_symlink():
        raise ContentError("Biên nhận hoàn tác không an toàn.")
    fields = as_mapping(read_json(receipt / "receipt.json"))
    if fields.get("ignored_names", []) != sorted(ignored_names):
        raise ContentError("Biên nhận không khớp loại thao tác hoàn tác.")
    measure = _measure(fields)
    if fields.get("status") not in ("applied", "prepared") or measure(
        receipt / "before"
    ) != fields.get("before"):
        raise ContentError("Bản sao lưu không khớp; chưa hoàn tác.")
    if directory.exists() and measure(directory, ignored_names=ignored_names) != fields.get(
        "after"
    ):
        raise ContentError("Nội dung đã thay đổi sau sửa; không ghi đè thay đổi của bạn.")
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


def latest_directory_change(history: Path) -> str:
    if history.is_symlink() or not history.exists():
        return ""
    for receipt in sorted(history.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
        if not receipt.is_dir() or receipt.is_symlink() or len(receipt.name) != 32:
            continue
        metadata = receipt / "receipt.json"
        if metadata.is_file() and not metadata.is_symlink() and (receipt / "before").is_dir():
            try:
                fields = as_mapping(read_json(metadata))
            except NostalgiaError:
                continue
            if fields.get("status") in ("applied", "prepared"):
                return receipt.name
    return ""
