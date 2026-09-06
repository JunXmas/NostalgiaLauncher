"""Mod, gói tài nguyên, shader cho một bản chơi."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.content.installed import list_installed, remove_installed, set_enabled
from nostalgia.content.installer import ContentInstallReport, install_project
from nostalgia.content.model import (
    ContentKind,
    InstalledContent,
    LoaderKind,
    Project,
    SearchPage,
    SortOrder,
)
from nostalgia.content.modrinth import PAGE_SIZE, search_projects
from nostalgia.facade.context import LauncherContext
from nostalgia.instance.store import load_instance
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.version_repo import VersionRepository

FABRIC_MAIN_CLASS_PREFIX = "net.fabricmc."


@dataclass(frozen=True, slots=True)
class ContentTarget:
    """Bản chơi nhìn từ phía nội dung: cài vào đâu, và cái gì mới tương thích."""

    instance_id: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind


class ContentOperations(LauncherContext):
    __slots__ = ()

    def describe_content_target(self, instance_id: str) -> ContentTarget:
        """Suy phiên bản game và loader từ version JSON của bản chơi. Không chạm mạng.

        Sau khi trộn kế thừa, `jar` trỏ về bản Mojang mà loader cưỡi lên — đó chính là
        phiên bản game để hỏi Modrinth. Bản thuần thì `jar` chính là `id`.
        """
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        loader_kind: LoaderKind = (
            "fabric" if version_meta.main_class.startswith(FABRIC_MAIN_CLASS_PREFIX) else "vanilla"
        )
        return ContentTarget(
            instance_id=instance_id,
            game_dir=self.paths.instance_dir(instance_id),
            game_version=version_meta.jar_version_id or version_meta.version_id,
            loader_kind=loader_kind,
        )

    def search_content(
        self,
        target: ContentTarget | None,
        content_kind: ContentKind,
        *,
        query: str = "",
        sort: SortOrder = "relevance",
        offset: int = 0,
        limit: int = PAGE_SIZE,
        game_versions: tuple[str, ...] | None = None,
        loaders: tuple[str, ...] | None = None,
        cancel_token: CancelToken | None = None,
    ) -> SearchPage:
        """Tìm trên Modrinth. Mặc định lọc theo bản chơi đích; giao diện có thể nới bộ lọc
        (nhiều phiên bản, nhiều loader) — khi đó `game_versions` / `loaders` đè lên. CHẠM MẠNG."""
        if game_versions is None:
            game_versions = (target.game_version,) if target else ()
        if loaders is None:
            loaders = (target.loader_kind,) if target else ()
        with self.make_http_client() as http_client:
            return search_projects(
                http_client,
                content_kind=content_kind,
                query=query,
                game_versions=game_versions,
                loaders=loaders,
                sort=sort,
                offset=offset,
                limit=limit,
                endpoints=self.endpoints,
                cancel_token=cancel_token,
            )

    def install_content(
        self,
        target: ContentTarget,
        project: Project,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> ContentInstallReport:
        """Cài dự án và phụ thuộc bắt buộc vào bản chơi. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            return install_project(
                http_client,
                project,
                target.game_dir,
                game_version=target.game_version,
                loader_kind=target.loader_kind,
                endpoints=self.endpoints,
                on_progress=on_progress,
                cancel_token=cancel_token,
            )

    def list_installed_content(
        self, target: ContentTarget, content_kind: ContentKind
    ) -> tuple[InstalledContent, ...]:
        return list_installed(target.game_dir, content_kind)

    def set_content_enabled(
        self, target: ContentTarget, content_kind: ContentKind, file_name: str, enabled: bool
    ) -> None:
        set_enabled(target.game_dir, content_kind, file_name, enabled)

    def remove_content(
        self, target: ContentTarget, content_kind: ContentKind, file_name: str
    ) -> None:
        remove_installed(target.game_dir, content_kind, file_name)
