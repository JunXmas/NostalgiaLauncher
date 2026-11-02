"""Tráo thư mục đã chuẩn bị, giữ bản trước và chỉ hoàn tác khi dữ liệu còn khớp."""

import hashlib
import shutil
import uuid
from pathlib import Path

from nostalgia.errors import ContentError, NostalgiaError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, read_json


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


def commit_directory(
    directory: Path,
    stage: Path,
    history: Path,
    original: str,
    *,
    ignored_names: frozenset[str] = frozenset(),
) -> str:
    if history.is_symlink() or tree_hash(directory) != original:
        raise ContentError("Nội dung đã thay đổi trong lúc chuẩn bị; không ghi đè.")
    receipt_id = uuid.uuid4().hex
    receipt = history / receipt_id
    receipt.mkdir(parents=True)
    directory.mkdir(exist_ok=True)
    after = tree_hash(stage, ignored_names=ignored_names)
    ignored: dict[str, JsonValue] = (
        {"ignored_names": list(sorted(ignored_names))} if ignored_names else {}
    )
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
    return receipt_id


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
    if fields.get("status") not in ("applied", "prepared") or tree_hash(
        receipt / "before"
    ) != fields.get("before"):
        raise ContentError("Bản sao lưu không khớp; chưa hoàn tác.")
    if directory.exists() and tree_hash(directory, ignored_names=ignored_names) != fields.get(
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
