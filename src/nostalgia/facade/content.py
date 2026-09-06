"""Mod, gói tài nguyên, shader cho một bản chơi — từ Modrinth hoặc CurseForge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from nostalgia.content import curseforge, modrinth
from nostalgia.content.installed import list_installed, remove_installed, set_enabled
from nostalgia.content.installer import ContentInstallReport, install_project
from nostalgia.content.model import (
    ContentKind,
    ContentSource,
    InstalledContent,
    Project,
    ProjectVersion,
    SearchPage,
    SortOrder,
)
from nostalgia.content.updates import ContentUpdate, find_updates, identify_by_hash
from nostalgia.facade.context import LauncherContext
from nostalgia.instance.store import load_instance
from nostalgia.modloader.model import COMPATIBLE_LOADERS, LoaderKind, detect_loader_kind
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.settings.store import Settings, load_settings, save_settings


@dataclass(frozen=True, slots=True)
class ContentTarget:
    """Bản chơi nhìn từ phía nội dung: cài vào đâu, và cái gì mới tương thích."""

    instance_id: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind


class ContentOperations(LauncherContext):
    __slots__ = ()

    # ----- cấu hình -----

    def load_settings(self) -> Settings:
        return load_settings(self.paths.config_dir)

    def save_settings(self, settings: Settings) -> None:
        save_settings(self.paths.config_dir, settings)

    # ----- bản chơi đích -----

    def describe_content_target(self, instance_id: str) -> ContentTarget:
        """Suy phiên bản game và loader của bản chơi. Không chạm mạng.

        Phiên bản game: sau khi trộn kế thừa, `jar` trỏ về bản Mojang mà loader cưỡi lên.
        Loader: theo mã bản (quy ước tên của từng loader) — trước đây chỉ nhận ra Fabric qua
        mainClass, nên bản Forge/NeoForge bị coi là vanilla và thư viện chặn cài mod.
        """
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        return ContentTarget(
            instance_id=instance_id,
            game_dir=self.paths.instance_dir(instance_id),
            game_version=version_meta.jar_version_id or version_meta.version_id,
            loader_kind=detect_loader_kind(instance.version_id),
        )

    # ----- tìm -----

    def search_content(
        self,
        target: ContentTarget | None,
        content_kind: ContentKind,
        *,
        source: ContentSource = "modrinth",
        query: str = "",
        sort: SortOrder = "relevance",
        offset: int = 0,
        limit: int = modrinth.PAGE_SIZE,
        game_versions: tuple[str, ...] | None = None,
        loaders: tuple[str, ...] | None = None,
        cancel_token: CancelToken | None = None,
    ) -> SearchPage:
        """Tìm ở một nguồn. Mặc định lọc theo bản chơi đích; giao diện có thể nới bộ lọc.
        CurseForge chỉ nhận một phiên bản và một loader mỗi lần. CHẠM MẠNG."""
        if game_versions is None:
            game_versions = (target.game_version,) if target else ()
        if loaders is None:
            loaders = COMPATIBLE_LOADERS[target.loader_kind] if target else ()
        with self.make_http_client() as http_client:
            if source == "curseforge":
                return curseforge.search_projects(
                    http_client,
                    self.load_settings().curseforge_api_key,
                    content_kind=content_kind,
                    query=query,
                    game_version=game_versions[0] if game_versions else "",
                    loader_kind=loaders[0] if loaders else "",
                    sort=sort,
                    offset=offset,
                    limit=limit,
                    endpoints=self.endpoints,
                    cancel_token=cancel_token,
                )
            return modrinth.search_projects(
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

    def fetch_versions(
        self, http_client: HttpClient, source: ContentSource, project_id: str
    ) -> tuple[ProjectVersion, ...]:
        """Danh sách bản của một dự án, theo nguồn của nó. CHẠM MẠNG."""
        if source == "curseforge":
            return curseforge.fetch_project_versions(
                http_client,
                self.load_settings().curseforge_api_key,
                project_id,
                endpoints=self.endpoints,
            )
        return modrinth.fetch_project_versions(http_client, project_id, endpoints=self.endpoints)

    # ----- cài và quản lý -----

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
                lambda project_id: self.fetch_versions(http_client, project.source, project_id),
                game_version=target.game_version,
                loader_kind=target.loader_kind,
                on_progress=on_progress,
                cancel_token=cancel_token,
            )

    def list_installed_content(
        self, target: ContentTarget, content_kind: ContentKind
    ) -> tuple[InstalledContent, ...]:
        return list_installed(target.game_dir, content_kind)

    def find_content_updates(
        self, target: ContentTarget, content_kind: ContentKind
    ) -> tuple[ContentUpdate, ...]:
        """Bản mới tương thích cho từng file có trong sổ. CHẠM MẠNG (một request mỗi dự án)."""
        installed = list_installed(target.game_dir, content_kind)
        with self.make_http_client() as http_client:
            return find_updates(
                installed,
                lambda source, project_id: self.fetch_versions(
                    http_client, cast(ContentSource, source), project_id
                ),
                game_version=target.game_version,
                loader_kind=target.loader_kind,
                content_kind=content_kind,
            )

    def update_content(
        self,
        target: ContentTarget,
        update: ContentUpdate,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> None:
        """Tải bản mới rồi gỡ file cũ (chỉ khi tải xong, để hỏng giữa chừng không mất mod)."""
        project = Project(
            project_id=update.installed.project_id,
            project_slug=update.installed.project_id,
            title=update.installed.label,
            description="",
            author="",
            content_kind=update.installed.content_kind,
            icon_url=update.installed.icon_url,
            downloads=0,
            follows=0,
            loaders=update.latest.loaders,
            source=cast(ContentSource, update.installed.source),
        )
        self.install_content(target, project, on_progress=on_progress, cancel_token=cancel_token)
        if update.latest.file_name != update.installed.file_name:
            remove_installed(
                target.game_dir, update.installed.content_kind, update.installed.file_name
            )

    def identify_installed_content(self, target: ContentTarget, content_kind: ContentKind) -> int:
        """Nhận diện file chép tay bằng sha1 trên Modrinth; trả số file nhận ra. CHẠM MẠNG."""
        installed = list_installed(target.game_dir, content_kind)
        with self.make_http_client() as http_client:
            return identify_by_hash(
                target.game_dir,
                content_kind,
                installed,
                lambda hashes: modrinth.lookup_versions_by_hash(
                    http_client, hashes, endpoints=self.endpoints
                ),
                lambda ids: modrinth.fetch_projects(
                    http_client, ids, content_kind, endpoints=self.endpoints
                ),
            )

    def set_content_enabled(
        self, target: ContentTarget, content_kind: ContentKind, file_name: str, enabled: bool
    ) -> None:
        set_enabled(target.game_dir, content_kind, file_name, enabled)

    def remove_content(
        self, target: ContentTarget, content_kind: ContentKind, file_name: str
    ) -> None:
        remove_installed(target.game_dir, content_kind, file_name)
