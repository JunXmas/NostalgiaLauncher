"""Cài một dự án vào bản chơi: chọn bản tương thích, gom phụ thuộc bắt buộc, tải, ghi sổ.

Phụ thuộc đi theo bề rộng, sâu tối đa `MAX_DEPENDENCY_DEPTH`, có tập đã-thăm — hai dự án
phụ thuộc chéo nhau là chuyện thật trên Modrinth, và không có tập đã-thăm thì vòng lặp
không bao giờ dừng.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from nostalgia.content.installed import LedgerEntry, content_dir, load_ledger, save_ledger
from nostalgia.content.model import LoaderKind, Project, ProjectVersion
from nostalgia.content.modrinth import choose_version
from nostalgia.errors import ContentError, NetworkError
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_all
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import resolve_child

MAX_DEPENDENCY_DEPTH = 3
# Mod là file nhỏ và Modrinth có hạn mức request; 4 luồng là đủ và lịch sự.
CONTENT_WORKERS = 4


# Cách lấy danh sách bản của một dự án theo id — Modrinth hay CurseForge tuỳ nguồn của dự án.
FetchVersionsFn = Callable[[str], tuple[ProjectVersion, ...]]


@dataclass(frozen=True, slots=True)
class ContentInstallReport:
    """Những gì đã vào thư mục bản chơi, dự án chính đứng đầu."""

    installed: tuple[ProjectVersion, ...]


def install_project(
    http_client: HttpClient,
    project: Project,
    game_dir: Path,
    fetch_versions: FetchVersionsFn,
    *,
    game_version: str,
    loader_kind: LoaderKind,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
) -> ContentInstallReport:
    """Cài `project` và mọi phụ thuộc bắt buộc còn thiếu. CHẠM MẠNG."""
    if project.content_kind == "modpack":
        message = "modpack không cài vào bản chơi có sẵn; nó thành một bản chơi mới"
        raise ContentError(message)
    if project.content_kind == "mod" and loader_kind == "vanilla":
        message = f"bản chơi không có mod loader, không cài được mod {project.title!r}"
        raise ContentError(message)
    directory = content_dir(game_dir, project.content_kind)
    ledger = load_ledger(directory)
    chosen = _resolve_with_dependencies(project, ledger, fetch_versions, game_version, loader_kind)
    tasks = [
        DownloadTask(
            url=project_version.file_url,
            destination=resolve_child(directory, project_version.file_name),
            sha1=project_version.file_sha1,
            size=project_version.file_size or None,
        )
        for project_version in chosen
    ]
    report = download_all(
        http_client,
        tasks,
        workers=CONTENT_WORKERS,
        on_progress=on_progress,
        cancel_token=cancel_token,
    )
    if not report.ok:
        first = report.failures[0]
        message = f"tải {project.title!r}: {first.task.url}: {first.reason}"
        raise NetworkError(message)
    for project_version in chosen:
        ledger[project_version.project_id] = LedgerEntry(
            project_id=project_version.project_id,
            title=project.title if project_version.project_id == project.project_id else "",
            version_id=project_version.version_id,
            version_number=project_version.version_number,
            file_name=project_version.file_name,
            icon_url=project.icon_url if project_version.project_id == project.project_id else "",
        )
    save_ledger(directory, ledger)
    return ContentInstallReport(installed=tuple(chosen))


def _resolve_with_dependencies(
    project: Project,
    ledger: dict[str, LedgerEntry],
    fetch_versions: FetchVersionsFn,
    game_version: str,
    loader_kind: LoaderKind,
) -> list[ProjectVersion]:
    chosen: list[ProjectVersion] = []
    visited: set[str] = {project.project_id}
    frontier: list[tuple[str, int]] = [(project.project_id, 0)]
    while frontier:
        project_id, depth = frontier.pop(0)
        versions = fetch_versions(project_id)
        project_version = choose_version(
            versions,
            game_version=game_version,
            loader_kind=loader_kind,
            content_kind=project.content_kind,
        )
        if project_version is None:
            if project_id != project.project_id:
                # Phụ thuộc không có bản khớp: bỏ qua, để người dùng còn cài được mod chính.
                continue
            message = (
                f"{project.title!r} không có bản nào cho Minecraft {game_version} với {loader_kind}"
            )
            raise ContentError(message)
        chosen.append(project_version)
        if depth >= MAX_DEPENDENCY_DEPTH:
            continue
        for dependency_id in project_version.required_project_ids:
            if dependency_id in visited or dependency_id in ledger:
                continue
            visited.add(dependency_id)
            frontier.append((dependency_id, depth + 1))
    return chosen
