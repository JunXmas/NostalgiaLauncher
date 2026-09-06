"""Modpack Modrinth (.mrpack) thành một bản chơi mới.

Thứ tự: tải .mrpack -> đọc chỉ mục -> cài loader đúng bản pack đòi -> đăng ký bản chơi -> tải
file của pack vào thư mục bản chơi -> chép overrides. Mọi bước đều đi qua đường sẵn có
(`install_loader`, `download_all`), nên tiến độ và huỷ hoạt động như cài bản thường.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from nostalgia.content import curseforge
from nostalgia.content.cfpack import apply_overrides as cf_apply_overrides
from nostalgia.content.cfpack import read_manifest, resolve_files
from nostalgia.content.model import Project, ProjectVersion
from nostalgia.content.mrpack import ALLOWED_HOSTS, apply_overrides, plan_downloads, read_index
from nostalgia.errors import ContentError, NetworkError
from nostalgia.facade.content import ContentOperations
from nostalgia.facade.loaders import LoaderOperations
from nostalgia.instance.model import Instance
from nostalgia.instance.store import create_instance, list_instances
from nostalgia.model.download import DownloadTask
from nostalgia.modloader.model import LoaderKind, detect_loader_kind
from nostalgia.net.download import download_all, download_one
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import ensure_dir

MODPACK_WORKERS = 8


@dataclass(frozen=True, slots=True)
class PackPlan:
    """Hai định dạng modpack, một luồng cài: cái gì cần biết trước, tải gì, chép gì."""

    name: str
    game_version: str
    loader_kind: LoaderKind
    loader_version: str
    tasks: Callable[[Path], list[DownloadTask]]
    apply_overrides: Callable[[Path], int]


def choose_pack_version(versions: tuple[ProjectVersion, ...], game_version: str) -> ProjectVersion:
    """Ưu tiên bản cho đúng phiên bản game đang lọc; trong đó release đứng trước beta."""
    matching = [v for v in versions if game_version and game_version in v.game_versions]
    pool = matching or list(versions)
    return next((v for v in pool if v.version_type == "release"), pool[0])


class ModpackOperations(LoaderOperations, ContentOperations):
    __slots__ = ()

    def install_modpack(
        self,
        project: Project,
        instance_id: str,
        display_name: str = "",
        *,
        game_version: str = "",
        allowed_hosts: tuple[str, ...] = ALLOWED_HOSTS,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> Instance:
        """Cài modpack Modrinth thành bản chơi `instance_id`. CHẠM MẠNG, có thể mất vài phút.

        `game_version` là phiên bản người dùng đang lọc: có bản pack cho đúng phiên bản đó
        thì lấy (release trước, không thì bản mới nhất), không có mới rơi về release mới
        nhất của pack. `allowed_hosts` chỉ để test trỏ vào máy chủ cục bộ.
        """
        if project.content_kind != "modpack":
            message = f"{project.title!r} không phải modpack"
            raise ContentError(message)
        if instance_id in {instance.instance_id for instance in list_instances(self.paths)}:
            message = f"đã có bản chơi {instance_id!r}"
            raise ContentError(message)
        with self.make_http_client() as http_client:
            versions = self.fetch_versions(http_client, project.source, project.project_id)
            chosen = choose_pack_version(versions, game_version)
            pack_path = ensure_dir(self.paths.data_dir / "installers") / chosen.file_name
            download_one(
                http_client,
                DownloadTask(url=chosen.file_url, destination=pack_path, sha1=chosen.file_sha1),
                cancel_token=cancel_token,
            )
            try:
                if project.source == "curseforge":
                    plan = self._plan_curseforge_pack(http_client, pack_path)
                else:
                    plan = self._plan_modrinth_pack(pack_path, allowed_hosts)
                self.install_loader(
                    plan.loader_kind,
                    plan.game_version,
                    plan.loader_version or None,
                    on_progress=on_progress,
                    cancel_token=cancel_token,
                )
                version_id = self._loader_version_id(plan.loader_kind, plan.game_version)
                instance = create_instance(
                    self.paths,
                    Instance(
                        instance_id=instance_id,
                        version_id=version_id,
                        display_name=display_name or plan.name,
                    ),
                )
                game_dir = self.paths.instance_dir(instance_id)
                report = download_all(
                    http_client,
                    plan.tasks(game_dir),
                    workers=MODPACK_WORKERS,
                    on_progress=on_progress,
                    cancel_token=cancel_token,
                )
                if not report.ok:
                    first = report.failures[0]
                    message = (
                        f"modpack thiếu {len(report.failures)} file; "
                        f"đầu tiên: {first.task.url}: {first.reason}"
                    )
                    raise NetworkError(message)
                plan.apply_overrides(game_dir)
            finally:
                pack_path.unlink(missing_ok=True)
        return instance

    def _plan_modrinth_pack(self, pack_path: Path, allowed_hosts: tuple[str, ...]) -> PackPlan:
        index = read_index(pack_path, allowed_hosts=allowed_hosts)
        return PackPlan(
            name=index.name,
            game_version=index.game_version,
            loader_kind=index.loader_kind,
            loader_version=index.loader_version,
            tasks=lambda game_dir: plan_downloads(index, game_dir),
            apply_overrides=lambda game_dir: apply_overrides(pack_path, game_dir),
        )

    def _plan_curseforge_pack(self, http_client: HttpClient, pack_path: Path) -> PackPlan:
        manifest = read_manifest(pack_path)
        api_key = self.load_settings().curseforge_api_key

        def fetch_one(project_id: str, file_id: str) -> ProjectVersion:
            return curseforge.fetch_file(
                http_client, api_key, project_id, file_id, endpoints=self.endpoints
            )

        return PackPlan(
            name=manifest.name,
            game_version=manifest.game_version,
            loader_kind=manifest.loader_kind,
            loader_version=manifest.loader_version,
            tasks=lambda game_dir: resolve_files(manifest, fetch_one, game_dir),
            apply_overrides=lambda game_dir: cf_apply_overrides(
                pack_path, game_dir, manifest.overrides_prefix
            ),
        )

    def _loader_version_id(self, loader_kind: str, game_version: str) -> str:
        """Mã bản vừa cài: bản mới nhất trong kho khớp loader + phiên bản game."""
        if loader_kind == "vanilla":
            return game_version
        candidates = [
            version_id
            for version_id in self.list_installed_versions()
            if detect_loader_kind(version_id) == loader_kind and version_id.endswith(game_version)
        ]
        if not candidates:
            message = f"không thấy bản {loader_kind} cho {game_version} sau khi cài"
            raise ContentError(message)
        return sorted(candidates)[-1]
