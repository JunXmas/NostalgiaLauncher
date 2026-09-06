"""Mod đã cài: có bản mới không, và file chép tay là dự án nào.

Cả hai đều thuần: nhận danh sách đã cài + hàm hỏi nguồn, trả về kết luận. Phần tải/ghi đi
qua `installer.py` như cài mới.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from nostalgia.content.installed import LedgerEntry, content_dir, load_ledger, save_ledger
from nostalgia.content.model import (
    ContentKind,
    InstalledContent,
    LoaderKind,
    Project,
    ProjectVersion,
)
from nostalgia.content.modrinth import choose_version
from nostalgia.storage.files import sha1_of_file

FetchVersionsFn = Callable[[str, str], tuple[ProjectVersion, ...]]  # (source, project_id)


@dataclass(frozen=True, slots=True)
class ContentUpdate:
    """Một file đã cài có bản mới hơn tương thích với bản chơi."""

    installed: InstalledContent
    latest: ProjectVersion


def find_updates(
    installed: tuple[InstalledContent, ...],
    fetch_versions: FetchVersionsFn,
    *,
    game_version: str,
    loader_kind: LoaderKind,
    content_kind: ContentKind,
) -> tuple[ContentUpdate, ...]:
    """File có trong sổ (biết dự án) và bản mới nhất tương thích khác bản đang cài."""
    updates: list[ContentUpdate] = []
    for installed_file in installed:
        if not installed_file.project_id:
            continue
        versions = fetch_versions(installed_file.source, installed_file.project_id)
        latest = choose_version(
            versions, game_version=game_version, loader_kind=loader_kind, content_kind=content_kind
        )
        if latest is not None and latest.version_id != installed_file.version_id:
            updates.append(ContentUpdate(installed=installed_file, latest=latest))
    return tuple(updates)


def identify_by_hash(
    game_dir: Path,
    content_kind: ContentKind,
    installed: tuple[InstalledContent, ...],
    lookup: Callable[[tuple[str, ...]], dict[str, ProjectVersion]],
    describe: Callable[[tuple[str, ...]], dict[str, Project]],
) -> int:
    """Băm những file chưa có trong sổ, hỏi Modrinth, ghi vào sổ. Trả số file nhận ra."""
    unknown = [installed_file for installed_file in installed if not installed_file.project_id]
    if not unknown:
        return 0
    directory = content_dir(game_dir, content_kind)
    by_hash: dict[str, InstalledContent] = {}
    for installed_file in unknown:
        path = directory / (
            installed_file.file_name
            if installed_file.enabled
            else installed_file.file_name + ".disabled"
        )
        if path.is_file():
            by_hash[sha1_of_file(path)] = installed_file
    matches = lookup(tuple(by_hash))
    if not matches:
        return 0
    projects = describe(tuple({project_version.project_id for project_version in matches.values()}))
    ledger = load_ledger(directory)
    for sha1, project_version in matches.items():
        if project_version.project_id in ledger:
            # Đã có một file của dự án này trong sổ (bản cài qua launcher): không đè dòng đó
            # bằng bản chép tay — sổ mỗi dự án một dòng, file lạ vẫn liệt kê được theo tên.
            continue
        project = projects.get(project_version.project_id)
        ledger[project_version.project_id] = LedgerEntry(
            project_id=project_version.project_id,
            title=project.title if project else "",
            version_id=project_version.version_id,
            version_number=project_version.version_number,
            file_name=by_hash[sha1].file_name,
            icon_url=project.icon_url if project else "",
            source="modrinth",
        )
    save_ledger(directory, ledger)
    return len(matches)
