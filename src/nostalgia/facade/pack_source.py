"""Tải đúng bản pack từ nguồn gốc và dựng nội dung trong vùng tạm trước khi đăng ký."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from nostalgia.content import curseforge, mrpack
from nostalgia.content.cfpack import apply_overrides as cf_apply_overrides
from nostalgia.content.cfpack import read_manifest, resolve_files
from nostalgia.content.model import ProjectVersion
from nostalgia.content.mrpack import apply_overrides, plan_downloads, read_index
from nostalgia.errors import ContentError, NetworkError
from nostalgia.facade.content import ContentOperations
from nostalgia.facade.loaders import LoaderOperations
from nostalgia.model.download import DownloadTask
from nostalgia.model.pack import PackReference
from nostalgia.modloader.model import LoaderKind
from nostalgia.net.download import download_all, download_one
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress


@dataclass(frozen=True, slots=True)
class PackPlan:
    name: str
    game_version: str
    loader_kind: LoaderKind
    loader_version: str
    tasks: Callable[[Path], list[DownloadTask]]
    apply_overrides: Callable[[Path], int]
    resolved_versions: list[ProjectVersion] = field(default_factory=list)


class PackSourceOperations(LoaderOperations, ContentOperations):
    __slots__ = ()

    def fetch_source_version(
        self, http_client: HttpClient, reference: PackReference, cancel_token: CancelToken
    ) -> ProjectVersion:
        chosen: ProjectVersion | None
        if reference.source == "curseforge":
            chosen = curseforge.fetch_file(
                http_client,
                self.load_settings().curseforge_api_key,
                reference.project_id,
                reference.version_id,
                endpoints=self.endpoints,
                cancel_token=cancel_token,
            )
        else:
            versions = self.fetch_versions(http_client, reference.source, reference.project_id)
            chosen = next(
                (
                    release
                    for release in versions
                    if release.version_id == reference.version_id
                    and release.project_id == reference.project_id
                ),
                None,
            )
            if chosen is None:
                raise ContentError("Không tìm thấy đúng bản phát hành của modpack/mod đã chia sẻ.")
        if chosen.project_id != reference.project_id or (
            reference.archive_sha1 and chosen.file_sha1 != reference.archive_sha1
        ):
            raise ContentError("File nguồn không khớp bản phát hành host đã chọn.")
        return chosen

    def sync_pack_source(
        self,
        reference: PackReference,
        game_dir: Path,
        game_version: str,
        loader_kind: LoaderKind,
        loader_version: str,
        *,
        cancel_token: CancelToken,
        on_progress: ProgressFn = ignore_progress,
    ) -> None:
        with (
            self.make_http_client() as http_client,
            TemporaryDirectory(prefix="pack-base-") as temporary,
        ):
            chosen = self.fetch_source_version(http_client, reference, cancel_token)
            pack_path = Path(temporary) / "base-pack.zip"
            download_one(
                http_client,
                DownloadTask(chosen.file_url, pack_path, chosen.file_sha1),
                cancel_token=cancel_token,
            )
            plan = (
                self._plan_curseforge_pack(http_client, pack_path)
                if reference.source == "curseforge"
                else self._plan_modrinth_pack(pack_path, None)
            )
            if (plan.game_version, plan.loader_kind, plan.loader_version) != (
                game_version,
                loader_kind,
                loader_version,
            ):
                raise ContentError("Pack gốc không khớp game và loader của phòng.")
            report = download_all(
                http_client,
                plan.tasks(game_dir),
                workers=8,
                cancel_token=cancel_token,
                on_progress=on_progress,
            )
            if not report.ok:
                raise NetworkError("Chưa tải đủ file của pack gốc.")
            cancel_token.raise_if_cancelled()
            plan.apply_overrides(game_dir)

    def _plan_modrinth_pack(
        self, pack_path: Path, allowed_hosts: tuple[str, ...] | None
    ) -> PackPlan:
        index = read_index(pack_path, allowed_hosts=allowed_hosts or mrpack.ALLOWED_HOSTS)
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
        resolved: list[ProjectVersion] = []

        def fetch_one(project_id: str, file_id: str) -> ProjectVersion:
            return curseforge.fetch_file(
                http_client, api_key, project_id, file_id, endpoints=self.endpoints
            )

        return PackPlan(
            name=manifest.name,
            game_version=manifest.game_version,
            loader_kind=manifest.loader_kind,
            loader_version=manifest.loader_version,
            tasks=lambda game_dir: resolve_files(
                manifest, fetch_one, game_dir, on_resolved=resolved.append
            ),
            apply_overrides=lambda game_dir: cf_apply_overrides(
                pack_path, game_dir, manifest.overrides_prefix
            ),
            resolved_versions=resolved,
        )
