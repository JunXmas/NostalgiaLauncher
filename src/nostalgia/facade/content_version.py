"""Danh sách bản mod tương thích và thay thế có hoàn tác cho từng bản chơi."""

from collections.abc import Callable
from typing import cast

from nostalgia.content import curseforge, modrinth
from nostalgia.content.mod_version import load_installed_mod, swap_mod_version, undo_mod_version
from nostalgia.content.model import ContentSource, ProjectVersion
from nostalgia.content.target import ContentTarget
from nostalgia.facade.content_detail import ContentDetailOperations
from nostalgia.instance.store import game_dir_of, load_instance
from nostalgia.modloader.model import detect_loader_kind
from nostalgia.modrepair.transaction import lock_mods
from nostalgia.net.http import HttpClient
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.settings.store import load_settings
from nostalgia.storage.directory_swap import latest_directory_change, recover_directory


class ContentVersionOperations(ContentDetailOperations):
    __slots__ = ()

    def describe_content_target(self, instance_id: str) -> ContentTarget:
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        return ContentTarget(
            instance_id,
            game_dir_of(self.paths, instance),
            version_meta.jar_version_id or version_meta.version_id,
            detect_loader_kind(instance.version_id),
        )

    def fetch_versions(
        self, http_client: HttpClient, source: ContentSource, project_id: str
    ) -> tuple[ProjectVersion, ...]:
        if source == "curseforge":
            return curseforge.fetch_project_versions(
                http_client,
                load_settings(self.paths.config_dir).curseforge_api_key,
                project_id,
                endpoints=self.endpoints,
            )
        return modrinth.fetch_project_versions(http_client, project_id, endpoints=self.endpoints)

    def fetch_mod_versions(self, instance_id: str, file_name: str) -> tuple[ProjectVersion, ...]:
        target = self.describe_content_target(instance_id)
        installed = load_installed_mod(target.game_dir, file_name)
        with self.make_http_client() as http_client:
            versions = self.fetch_versions(
                http_client, cast(ContentSource, installed.source), installed.project_id
            )
        return tuple(
            sorted(
                (
                    release
                    for release in versions
                    if release.supports(target.game_version, target.loader_kind, "mod")
                ),
                key=lambda release: release.date_published,
                reverse=True,
            )
        )

    def swap_mod_version(
        self,
        instance_id: str,
        file_name: str,
        version_id: str,
        is_running: Callable[[], bool],
        *,
        on_progress: ProgressFn = ignore_progress,
    ) -> str:
        target = self.describe_content_target(instance_id)
        installed = load_installed_mod(target.game_dir, file_name)
        with self.make_http_client() as http_client:
            return swap_mod_version(
                target,
                file_name,
                version_id,
                http_client,
                lambda project_id: self.fetch_versions(
                    http_client, cast(ContentSource, installed.source), project_id
                ),
                is_running,
                on_progress,
            )

    def undo_mod_version(
        self, instance_id: str, receipt_id: str, is_running: Callable[[], bool]
    ) -> None:
        instance = load_instance(self.paths, instance_id)
        undo_mod_version(game_dir_of(self.paths, instance), receipt_id, is_running)

    def recover_interrupted_mod_change(self, instance_id: str) -> None:
        """Lần đổi phiên bản/sửa mod trước bị cắt ngang (máy tắt) thì trả bộ mod cũ về trước khi
        game chạy và tự tạo một thư mục mods rỗng."""
        game_dir = game_dir_of(self.paths, load_instance(self.paths, instance_id))
        with lock_mods(game_dir):
            for history in (
                ".nostalgia-mod-versions",
                ".nostalgia-repairs",
                ".nostalgia-nos-updates",
            ):
                recover_directory(game_dir / "mods", game_dir / history)

    def latest_mod_version_change(self, instance_id: str) -> str:
        instance = load_instance(self.paths, instance_id)
        return latest_directory_change(
            game_dir_of(self.paths, instance) / ".nostalgia-mod-versions"
        )
