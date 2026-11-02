"""Mod, gói tài nguyên, shader cho một bản chơi — từ Modrinth hoặc CurseForge."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from nostalgia.content import curseforge, modrinth
from nostalgia.content.installed import content_dir, list_installed, remove_installed, set_enabled
from nostalgia.content.installer import ContentInstallReport, install_project
from nostalgia.content.local_metadata import refresh_metadata
from nostalgia.content.model import (
    ContentKind,
    ContentSource,
    InstalledContent,
    Project,
    SearchPage,
    SortOrder,
)
from nostalgia.content.target import ContentTarget
from nostalgia.content.updates import ContentUpdate, find_updates, identify_by_hash
from nostalgia.facade.content_version import ContentVersionOperations
from nostalgia.modloader.model import COMPATIBLE_LOADERS
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.settings.store import Settings, load_settings, save_settings


class ContentOperations(ContentVersionOperations):
    __slots__ = ()

    # ----- cấu hình -----

    def load_settings(self) -> Settings:
        return load_settings(self.paths.config_dir)

    def save_settings(self, settings: Settings) -> None:
        save_settings(self.paths.config_dir, settings)

    # ----- bản chơi đích -----

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

    # ----- cài và quản lý -----

    def install_content(
        self,
        target: ContentTarget,
        project: Project,
        *,
        version_id: str = "",
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
                version_id=version_id,
                on_progress=on_progress,
                cancel_token=cancel_token,
            )

    def content_directory(self, target: ContentTarget, content_kind: ContentKind) -> Path:
        """Thư mục nội dung để UI theo dõi thay đổi file, không cần biết layout lõi."""
        return content_dir(target.game_dir, content_kind)

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

    def identify_installed_content(self, target: ContentTarget, content_kind: ContentKind) -> int:
        """Nhận diện file chép tay bằng sha1 trên Modrinth; trả số file nhận ra. CHẠM MẠNG."""
        installed = self.scan_installed_content(target, content_kind)
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

    def scan_installed_content(
        self, target: ContentTarget, content_kind: ContentKind
    ) -> tuple[InstalledContent, ...]:
        """Đọc tên/phiên bản JAR và cache cục bộ. Gọi ở worker; không mạng."""
        installed = list_installed(target.game_dir, content_kind)
        if content_kind == "mod":
            refresh_metadata(content_dir(target.game_dir, content_kind), installed)
            installed = list_installed(target.game_dir, content_kind)
        return installed

    def set_content_enabled(
        self, target: ContentTarget, content_kind: ContentKind, file_name: str, enabled: bool
    ) -> None:
        set_enabled(target.game_dir, content_kind, file_name, enabled)

    def remove_content(
        self, target: ContentTarget, content_kind: ContentKind, file_name: str
    ) -> None:
        remove_installed(target.game_dir, content_kind, file_name)
