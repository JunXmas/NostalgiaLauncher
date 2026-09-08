"""Kho skin đã có trong launcher: skin tải về cho tài khoản, skin đã upload, skin tự nhập.

Mỗi skin một cặp file `<entry_id>.png` + `<entry_id>.json` trong `skins_dir/library/`.
`entry_id` là 12 ký tự đầu sha1 của ảnh, nên cùng một skin được thêm lại (tải lại cho tài
khoản, upload lại) không nhân đôi. Ảnh phải là PNG và nhỏ (skin thật ~4 KB): kho này không
phải chỗ chứa ảnh bậy được kéo nhầm vào.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import DataFileError, SkinError
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, ensure_dir, read_json

LIBRARY_DIR_NAME = "library"
MAX_SKIN_BYTES = 256 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DIGEST_LENGTH = 12

SOURCE_LABELS = {
    "microsoft": "Mojang",
    "ely": "Ely.by",
    "upload": "Đã upload",
    "import": "Tự nhập",
}


@dataclass(frozen=True, slots=True)
class SkinEntry:
    """Một skin trong kho. `source`: microsoft | ely | upload | import."""

    entry_id: str
    name: str
    slim: bool
    source: str
    added_at: int
    skin_path: Path

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS.get(self.source, self.source)


def library_dir(skins_dir: Path) -> Path:
    return skins_dir / LIBRARY_DIR_NAME


def digest_of(content: bytes) -> str:
    """Khoá nhận diện một ảnh skin; cùng khoá là cùng skin."""
    return hashlib.sha1(content, usedforsecurity=False).hexdigest()[:DIGEST_LENGTH]


def digest_of_file(path: Path) -> str:
    try:
        return digest_of(path.read_bytes())
    except OSError:
        return ""


def check_skin_png(content: bytes) -> None:
    if not content.startswith(PNG_SIGNATURE):
        raise SkinError("file skin phải là ảnh PNG")
    if len(content) > MAX_SKIN_BYTES:
        raise SkinError(f"file skin quá lớn: {len(content)} byte (tối đa {MAX_SKIN_BYTES})")


def list_library(skins_dir: Path) -> tuple[SkinEntry, ...]:
    """Mới nhất trước. Cặp file lệch (thiếu png hoặc json hỏng) bị bỏ qua, không chặn kho."""
    directory = library_dir(skins_dir)
    if not directory.is_dir():
        return ()
    found = [
        skin_entry
        for json_path in directory.glob("*.json")
        if (skin_entry := _load_entry(json_path)) is not None
    ]
    return tuple(sorted(found, key=lambda skin_entry: (-skin_entry.added_at, skin_entry.name)))


def find_entry(skins_dir: Path, entry_id: str) -> SkinEntry | None:
    return _load_entry(library_dir(skins_dir) / f"{entry_id}.json")


def add_to_library(
    skins_dir: Path,
    png_path: Path,
    *,
    name: str,
    slim: bool,
    source: str,
    now: float | None = None,
) -> SkinEntry:
    """Thêm (hoặc trả về bản đã có) một skin. Ném `SkinError` nếu không phải PNG nhỏ."""
    try:
        content = png_path.read_bytes()
    except OSError as exc:
        raise SkinError(f"không đọc được file skin: {png_path}") from exc
    check_skin_png(content)
    entry_id = digest_of(content)
    existing = find_entry(skins_dir, entry_id)
    if existing is not None:
        return existing
    directory = ensure_dir(library_dir(skins_dir))
    skin_path = directory / f"{entry_id}.png"
    skin_path.write_bytes(content)
    added_at = int(time.time() if now is None else now)
    document: JsonValue = {
        "name": name.strip() or entry_id,
        "slim": slim,
        "source": source,
        "added_at": added_at,
    }
    atomic_write_json(directory / f"{entry_id}.json", document)
    return SkinEntry(entry_id, name.strip() or entry_id, slim, source, added_at, skin_path)


def remove_from_library(skins_dir: Path, entry_id: str) -> None:
    """Gỡ một skin khỏi kho; không có thì thôi."""
    directory = library_dir(skins_dir)
    for suffix in (".json", ".png"):
        (directory / f"{entry_id}{suffix}").unlink(missing_ok=True)


def _load_entry(json_path: Path) -> SkinEntry | None:
    skin_path = json_path.with_suffix(".png")
    if not json_path.is_file() or not skin_path.is_file():
        return None
    try:
        fields = as_mapping(read_json(json_path))
    except DataFileError:
        return None
    slim = fields.get("slim")
    return SkinEntry(
        entry_id=json_path.stem,
        name=as_string(fields.get("name")) or json_path.stem,
        slim=slim if isinstance(slim, bool) else False,
        source=as_string(fields.get("source")) or "import",
        added_at=as_integer(fields.get("added_at")) or 0,
        skin_path=skin_path,
    )
