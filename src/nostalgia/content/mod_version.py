"""Đổi bản mod trong vùng tạm, giữ cả thư mục trước đổi để hoàn tác."""

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import cast

from nostalgia.content.installed import LEDGER_FILE_NAME, list_installed, load_ledger, set_enabled
from nostalgia.content.installer import FetchVersionsFn, _directory_lock, install_project
from nostalgia.content.local_metadata import CACHE_FILE
from nostalgia.content.model import ContentSource, InstalledContent, Project, ProjectVersion
from nostalgia.content.modrinth import choose_version
from nostalgia.content.target import ContentTarget
from nostalgia.errors import ContentError
from nostalgia.modrepair.transaction import lock_mods
from nostalgia.net.http import HttpClient
from nostalgia.operations.progress import ProgressFn
from nostalgia.storage.directory_swap import commit_directory, tree_hash, undo_directory
from nostalgia.storage.files import resolve_child


def load_installed_mod(game_dir: Path, file_name: str) -> InstalledContent:
    installed = next(
        (mod for mod in list_installed(game_dir, "mod") if mod.file_name == file_name), None
    )
    if (
        installed is None
        or not installed.project_id
        or installed.source not in ("modrinth", "curseforge")
    ):
        raise ContentError("Hãy nhận diện mod trong danh sách đã cài trước khi đổi phiên bản.")
    return installed


def swap_mod_version(
    target: ContentTarget,
    file_name: str,
    version_id: str,
    http_client: HttpClient,
    fetch_versions: FetchVersionsFn,
    is_running: Callable[[], bool],
    on_progress: ProgressFn,
) -> str:
    directory = target.game_dir / "mods"
    with lock_mods(target.game_dir), _directory_lock(directory):
        if is_running():
            raise ContentError("Tắt Minecraft trước khi đổi phiên bản mod.")
        installed = load_installed_mod(target.game_dir, file_name)
        if installed.version_id == version_id:
            raise ContentError("Mod đang dùng phiên bản này.")
        original = tree_hash(directory)
        project = Project(
            installed.project_id,
            installed.project_id,
            installed.label,
            "",
            "",
            "mod",
            installed.icon_url,
            0,
            0,
            (),
            cast(ContentSource, installed.source),
        )
        with tempfile.TemporaryDirectory(
            prefix=".nostalgia-version-", dir=target.game_dir
        ) as temporary:
            stage = Path(temporary)
            shutil.copytree(directory, stage / "mods")
            ledger = load_ledger(stage / "mods")

            def checked_versions(project_id: str) -> tuple[ProjectVersion, ...]:
                versions = fetch_versions(project_id)
                chosen = choose_version(
                    tuple(
                        release
                        for release in versions
                        if project_id != project.project_id or release.version_id == version_id
                    ),
                    game_version=target.game_version,
                    loader_kind=target.loader_kind,
                    content_kind="mod",
                )
                if chosen is None:
                    raise ContentError(
                        "Không có phiên bản hoặc phụ thuộc tương thích; giữ nguyên bản cũ."
                    )
                candidate = resolve_child(stage / "mods", chosen.file_name)
                old = ledger.get(project_id)
                if candidate.exists() and (old is None or old.file_name != chosen.file_name):
                    raise ContentError("Tên file bản mới trùng mod khác; không ghi đè.")
                return versions

            report = install_project(
                http_client,
                project,
                stage,
                checked_versions,
                game_version=target.game_version,
                loader_kind=target.loader_kind,
                version_id=version_id,
                on_progress=on_progress,
            )
            staged = load_ledger(stage / "mods")
            for release in report.installed:
                for dependency_id in release.required_project_ids:
                    dependency = staged.get(dependency_id)
                    if (
                        dependency is None
                        or not resolve_child(stage / "mods", dependency.file_name).is_file()
                    ):
                        raise ContentError("Thiếu phụ thuộc bắt buộc; chưa thay phiên bản mod.")
            if not installed.enabled:
                set_enabled(stage, "mod", report.installed[0].file_name, False)
            if is_running():
                raise ContentError("Minecraft vừa khởi chạy; giữ nguyên bộ mod cũ.")
            return commit_directory(
                directory,
                stage / "mods",
                target.game_dir / ".nostalgia-mod-versions",
                original,
                ignored_names=frozenset({LEDGER_FILE_NAME, CACHE_FILE}),
            )


def undo_mod_version(game_dir: Path, receipt_id: str, is_running: Callable[[], bool]) -> None:
    with lock_mods(game_dir), _directory_lock(game_dir / "mods"):
        if is_running():
            raise ContentError("Tắt Minecraft trước khi hoàn tác phiên bản mod.")
        undo_directory(
            game_dir / "mods",
            game_dir / ".nostalgia-mod-versions",
            receipt_id,
            ignored_names=frozenset({LEDGER_FILE_NAME, CACHE_FILE}),
        )
