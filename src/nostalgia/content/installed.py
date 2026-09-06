"""Những gì đang nằm trong `mods/`, `resourcepacks/`, `shaderpacks/` của một bản chơi.

Sổ theo dõi `.nostalgia-installed.json` nằm ngay trong thư mục đó: xoá thư mục là xoá sổ,
không bao giờ có sổ mồ côi. File không có trong sổ (người dùng chép tay) vẫn được liệt kê,
chỉ thiếu tên dự án.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.content.model import FOLDER_BY_KIND, ContentKind, InstalledContent
from nostalgia.errors import ContentError, DataFileError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, ensure_dir, read_json, resolve_child

LEDGER_FILE_NAME = ".nostalgia-installed.json"
# Tắt mod bằng đuôi `.disabled` — đúng quy ước Fabric/Forge, nên tắt bằng launcher khác vẫn thấy.
DISABLED_SUFFIX = ".disabled"
ACCEPTED_SUFFIXES: dict[ContentKind, tuple[str, ...]] = {
    "mod": (".jar",),
    "resourcepack": (".zip",),
    "shader": (".zip",),
}


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """Một dòng sổ: file này đến từ dự án nào, bản nào."""

    project_id: str
    title: str
    version_id: str
    version_number: str
    file_name: str
    icon_url: str = ""


def content_dir(game_dir: Path, content_kind: ContentKind) -> Path:
    return game_dir / FOLDER_BY_KIND[content_kind]


def list_installed(game_dir: Path, content_kind: ContentKind) -> tuple[InstalledContent, ...]:
    """File trong thư mục, sắp theo tên; ghép với sổ để lấy tên dự án. Không chạm mạng."""
    directory = content_dir(game_dir, content_kind)
    if not directory.is_dir():
        return ()
    by_file_name = {
        ledger_entry.file_name: ledger_entry for ledger_entry in load_ledger(directory).values()
    }
    found: list[InstalledContent] = []
    for path in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        enabled = not path.name.endswith(DISABLED_SUFFIX)
        file_name = path.name if enabled else path.name.removesuffix(DISABLED_SUFFIX)
        if not file_name.lower().endswith(ACCEPTED_SUFFIXES[content_kind]):
            continue
        ledger_entry = by_file_name.get(file_name)
        found.append(
            InstalledContent(
                content_kind=content_kind,
                file_name=file_name,
                file_size=path.stat().st_size,
                enabled=enabled,
                project_id=ledger_entry.project_id if ledger_entry else "",
                title=ledger_entry.title if ledger_entry else "",
                version_id=ledger_entry.version_id if ledger_entry else "",
                version_number=ledger_entry.version_number if ledger_entry else "",
                icon_url=ledger_entry.icon_url if ledger_entry else "",
            )
        )
    return tuple(found)


def set_enabled(game_dir: Path, content_kind: ContentKind, file_name: str, enabled: bool) -> None:
    """Bật/tắt bằng đổi tên. Gọi lại với trạng thái hiện tại thì không làm gì."""
    directory = content_dir(game_dir, content_kind)
    active = resolve_child(directory, file_name)
    disabled = resolve_child(directory, file_name + DISABLED_SUFFIX)
    source, target = (disabled, active) if enabled else (active, disabled)
    if target.exists() or not source.exists():
        return
    source.rename(target)


def remove_installed(game_dir: Path, content_kind: ContentKind, file_name: str) -> None:
    """Xoá file (dù đang bật hay tắt) và dòng sổ của nó."""
    directory = content_dir(game_dir, content_kind)
    removed = False
    for candidate in (file_name, file_name + DISABLED_SUFFIX):
        path = resolve_child(directory, candidate)
        if path.is_file():
            path.unlink()
            removed = True
    if not removed:
        message = f"không có file {file_name!r} trong {directory}"
        raise ContentError(message)
    ledger = load_ledger(directory)
    remaining = {
        pid: ledger_entry
        for pid, ledger_entry in ledger.items()
        if ledger_entry.file_name != file_name
    }
    if len(remaining) != len(ledger):
        save_ledger(directory, remaining)


def load_ledger(directory: Path) -> dict[str, LedgerEntry]:
    """Sổ theo dõi; sổ hỏng thì coi như rỗng chứ không làm hỏng cả danh sách."""
    path = directory / LEDGER_FILE_NAME
    if not path.is_file():
        return {}
    try:
        document = read_json(path)
    except DataFileError:
        return {}
    ledger: dict[str, LedgerEntry] = {}
    for project_id, raw in as_mapping(document).items():
        fields = as_mapping(raw)
        file_name = as_string(fields.get("file_name"))
        if not file_name:
            continue
        ledger[project_id] = LedgerEntry(
            project_id=project_id,
            title=as_string(fields.get("title")) or "",
            version_id=as_string(fields.get("version_id")) or "",
            version_number=as_string(fields.get("version_number")) or "",
            file_name=file_name,
            icon_url=as_string(fields.get("icon_url")) or "",
        )
    return ledger


def save_ledger(directory: Path, ledger: dict[str, LedgerEntry]) -> None:
    document: dict[str, JsonValue] = {
        project_id: {
            "title": ledger_entry.title,
            "version_id": ledger_entry.version_id,
            "version_number": ledger_entry.version_number,
            "file_name": ledger_entry.file_name,
            "icon_url": ledger_entry.icon_url,
        }
        for project_id, ledger_entry in ledger.items()
    }
    atomic_write_json(ensure_dir(directory) / LEDGER_FILE_NAME, document)
