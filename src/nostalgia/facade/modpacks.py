"""Modpack Modrinth (.mrpack) thành một bản chơi mới.

Thứ tự: tải .mrpack -> đọc chỉ mục -> cài loader đúng bản pack đòi -> đăng ký bản chơi -> tải
file của pack vào thư mục bản chơi -> chép overrides. Mọi bước đều đi qua đường sẵn có
(`install_loader`, `download_all`), nên tiến độ và huỷ hoạt động như cài bản thường.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from nostalgia.content import modrinth
from nostalgia.content.model import Project
from nostalgia.content.pack_inventory import record_pack_inventory
from nostalgia.content.pack_origin import save_pack_origin
from nostalgia.content.pack_version import choose_pack_version as choose_pack_version
from nostalgia.errors import ContentError, NetworkError
from nostalgia.facade.instances import InstanceOperations
from nostalgia.facade.pack_source import PackPlan, PackSourceOperations
from nostalgia.instance.model import Instance
from nostalgia.model.download import DownloadTask
from nostalgia.model.pack import PackReference
from nostalgia.net.download import download_all, download_one
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import ensure_dir, sha1_of_file

MODPACK_WORKERS = 8


class ModpackOperations(PackSourceOperations, InstanceOperations):
    __slots__ = ()

    def install_modpack(
        self,
        project: Project,
        instance_id: str,
        display_name: str = "",
        *,
        game_version: str = "",
        version_id: str = "",
        game_dir_override: str = "",
        allowed_hosts: tuple[str, ...] | None = None,
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
        self.require_instance_id_free(instance_id)
        with self.make_http_client() as http_client:
            versions = self.fetch_versions(http_client, project.source, project.project_id)
            chosen = choose_pack_version(
                versions, game_version, project_id=project.project_id, version_id=version_id
            )
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
                if version_id and game_version and plan.game_version != game_version:
                    raise ContentError(
                        "modpack archive does not match the selected Minecraft version"
                    )
                instance = self._install_pack_plan(
                    http_client,
                    plan,
                    instance_id,
                    display_name,
                    icon_url=project.icon_url,
                    origin=PackReference(
                        project.source,
                        project.project_id,
                        chosen.version_id,
                        chosen.file_sha1,
                        project.title[:160],
                    ),
                    game_dir_override=game_dir_override,
                    on_progress=on_progress,
                    cancel_token=cancel_token,
                )
            finally:
                pack_path.unlink(missing_ok=True)
        return instance

    def install_modpack_file(
        self,
        pack_path: Path,
        instance_id: str,
        display_name: str = "",
        *,
        game_dir_override: str = "",
        allowed_hosts: tuple[str, ...] | None = None,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> Instance:
        """Modpack từ file trên máy: .mrpack (Modrinth) hoặc .zip có manifest.json (CurseForge).
        Nhận dạng theo nội dung chứ không theo đuôi file. CHẠM MẠNG để tải mod."""
        self.require_instance_id_free(instance_id)
        with self.make_http_client() as http_client, zipfile.ZipFile(pack_path) as archive:
            names = set(archive.namelist())
            if "modrinth.index.json" in names:
                plan = self._plan_modrinth_pack(pack_path, allowed_hosts)
            elif "manifest.json" in names:
                plan = self._plan_curseforge_pack(http_client, pack_path)
            else:
                message = f"{pack_path.name} không phải modpack Modrinth (.mrpack) hay CurseForge"
                raise ContentError(message)
            return self._install_pack_plan(
                http_client,
                plan,
                instance_id,
                display_name,
                origin=self._fetch_import_origin(http_client, pack_path, cancel_token),
                game_dir_override=game_dir_override,
                on_progress=on_progress,
                cancel_token=cancel_token,
            )

    def _install_pack_plan(
        self,
        http_client: HttpClient,
        plan: PackPlan,
        instance_id: str,
        display_name: str,
        *,
        icon_url: str = "",
        origin: PackReference | None = None,
        game_dir_override: str = "",
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> Instance:
        """Phần chung của mọi modpack: cài loader, đăng ký bản chơi, tải file, chép overrides."""
        loader_report = self.install_loader(
            plan.loader_kind,
            plan.game_version,
            plan.loader_version or None,
            on_progress=on_progress,
            cancel_token=cancel_token,
        )
        instance = self.create_instance(
            Instance(
                instance_id=instance_id,
                version_id=loader_report.version_meta.version_id,
                display_name=display_name or plan.name,
                icon_url=icon_url,
                game_dir_override=game_dir_override,
            )
        )
        game_dir = self.instance_game_dir(instance)
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
        if origin is not None:
            save_pack_origin(
                game_dir, origin, plan.game_version, plan.loader_kind, plan.loader_version
            )
        record_pack_inventory(game_dir, plan.resolved_versions)
        return instance

    def _fetch_import_origin(
        self, http_client: HttpClient, pack_path: Path, cancel_token: CancelToken | None
    ) -> PackReference | None:
        digest = sha1_of_file(pack_path)
        try:
            found = modrinth.lookup_versions_by_hash(
                http_client, (digest,), endpoints=self.endpoints, cancel_token=cancel_token
            )
        except (ContentError, NetworkError):
            return None
        chosen = found.get(digest)
        if chosen is None or chosen.file_sha1 != digest:
            return None
        return PackReference("modrinth", chosen.project_id, chosen.version_id, digest)
