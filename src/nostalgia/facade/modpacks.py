"""Modpack Modrinth (.mrpack) thành một bản chơi mới.

Thứ tự: tải .mrpack -> đọc chỉ mục -> cài loader đúng bản pack đòi -> đăng ký bản chơi -> tải
file của pack vào thư mục bản chơi -> chép overrides. Mọi bước đều đi qua đường sẵn có
(`install_loader`, `download_all`), nên tiến độ và huỷ hoạt động như cài bản thường.
"""

from __future__ import annotations

from nostalgia.content.model import Project
from nostalgia.content.modrinth import fetch_project_versions
from nostalgia.content.mrpack import ALLOWED_HOSTS, apply_overrides, plan_downloads, read_index
from nostalgia.errors import ContentError, NetworkError
from nostalgia.facade.loaders import LoaderOperations
from nostalgia.instance.model import Instance
from nostalgia.instance.store import create_instance, list_instances
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_all, download_one
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import ensure_dir

MODPACK_WORKERS = 8


class ModpackOperations(LoaderOperations):
    __slots__ = ()

    def install_modpack(
        self,
        project: Project,
        instance_id: str,
        display_name: str = "",
        *,
        allowed_hosts: tuple[str, ...] = ALLOWED_HOSTS,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> Instance:
        """Cài modpack Modrinth thành bản chơi `instance_id`. CHẠM MẠNG, có thể mất vài phút.

        `allowed_hosts` chỉ để test trỏ vào máy chủ cục bộ.
        """
        if project.source != "modrinth" or project.content_kind != "modpack":
            message = f"{project.title!r} không phải modpack Modrinth"
            raise ContentError(message)
        if instance_id in {instance.instance_id for instance in list_instances(self.paths)}:
            message = f"đã có bản chơi {instance_id!r}"
            raise ContentError(message)
        with self.make_http_client() as http_client:
            versions = fetch_project_versions(
                http_client, project.project_id, endpoints=self.endpoints
            )
            chosen = next((v for v in versions if v.version_type == "release"), versions[0])
            mrpack_path = ensure_dir(self.paths.data_dir / "installers") / chosen.file_name
            download_one(
                http_client,
                DownloadTask(url=chosen.file_url, destination=mrpack_path, sha1=chosen.file_sha1),
                cancel_token=cancel_token,
            )
            try:
                index = read_index(mrpack_path, allowed_hosts=allowed_hosts)
                self.install_loader(
                    index.loader_kind,
                    index.game_version,
                    index.loader_version or None,
                    on_progress=on_progress,
                    cancel_token=cancel_token,
                )
                version_id = self._loader_version_id(index.loader_kind, index.game_version)
                instance = create_instance(
                    self.paths,
                    Instance(
                        instance_id=instance_id,
                        version_id=version_id,
                        display_name=display_name or index.name,
                    ),
                )
                game_dir = self.paths.instance_dir(instance_id)
                report = download_all(
                    http_client,
                    plan_downloads(index, game_dir),
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
                apply_overrides(mrpack_path, game_dir)
            finally:
                mrpack_path.unlink(missing_ok=True)
        return instance

    def _loader_version_id(self, loader_kind: str, game_version: str) -> str:
        """Mã bản vừa cài: bản mới nhất trong kho khớp loader + phiên bản game."""
        if loader_kind == "vanilla":
            return game_version
        candidates = [
            version_id
            for version_id in self.list_installed_versions()
            if loader_kind in version_id and game_version in version_id
        ]
        if not candidates:
            message = f"không thấy bản {loader_kind} cho {game_version} sau khi cài"
            raise ContentError(message)
        return sorted(candidates)[-1]
