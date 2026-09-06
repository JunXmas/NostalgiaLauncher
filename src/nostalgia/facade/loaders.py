"""Mod loader: liệt kê bản và cài Fabric / Forge / NeoForge cho một phiên bản game.

Mọi loader kết thúc ở cùng một chỗ: một `version_id` mới trong kho, rồi `install_version` cài
nốt phần thiếu. Forge/NeoForge cần Java để chạy installer, nên cài bản gốc trước để có JRE.
"""

from __future__ import annotations

from nostalgia.errors import VersionError
from nostalgia.facade.versions import VersionOperations
from nostalgia.launch.runner import InstallReport, resolve_installed_java_binary
from nostalgia.modloader.fabric import fetch_fabric_loader_versions, install_fabric_profile
from nostalgia.modloader.forge import fetch_forge_versions, fetch_neoforge_versions, run_installer
from nostalgia.modloader.model import LoaderKind, LoaderVersion
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress

INSTALLER_STAGE = "chạy installer"


class LoaderOperations(VersionOperations):
    __slots__ = ()

    def list_loader_versions(
        self, loader_kind: LoaderKind, game_version: str
    ) -> tuple[LoaderVersion, ...]:
        """Các bản loader dùng được với `game_version`, mới nhất đứng đầu. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            return self._fetch_loader_versions(http_client, loader_kind, game_version, None)

    def install_loader(
        self,
        loader_kind: LoaderKind,
        game_version: str,
        loader_version: str | None = None,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> InstallReport:
        """Cài loader cho `game_version`; bỏ trống `loader_version` thì lấy bản ổn định mới
        nhất. CHẠM MẠNG. Trả về báo cáo cài của chính bản loader vừa sinh ra."""
        if loader_kind == "vanilla":
            return self.install_version(
                game_version, on_progress=on_progress, cancel_token=cancel_token
            )
        with self.make_http_client() as http_client:
            candidates = self._fetch_loader_versions(
                http_client, loader_kind, game_version, cancel_token
            )
            chosen = self._pick(candidates, loader_version)
            if loader_kind == "fabric":
                version_id = install_fabric_profile(
                    http_client,
                    self.paths,
                    game_version,
                    chosen.loader_version,
                    endpoints=self.endpoints,
                    cancel_token=cancel_token,
                )
            else:
                # Installer cần Java: cài bản gốc trước, JRE Mojang đi kèm theo đó.
                base = self.install_version(
                    game_version, on_progress=on_progress, cancel_token=cancel_token
                )
                java_binary = resolve_installed_java_binary(
                    base.version_meta, self.platform, self.paths
                )
                if java_binary is None:
                    message = f"không có Java để chạy installer {loader_kind} cho {game_version}"
                    raise VersionError(message)
                on_progress(Progress(stage=INSTALLER_STAGE, done=0, total=0))
                version_id = run_installer(
                    http_client,
                    self.paths.data_dir,
                    self.paths.versions_dir,
                    java_binary,
                    chosen.installer_url,
                    cancel_token=cancel_token,
                )
        return self.install_version(version_id, on_progress=on_progress, cancel_token=cancel_token)

    def _fetch_loader_versions(
        self,
        http_client: HttpClient,
        loader_kind: LoaderKind,
        game_version: str,
        cancel_token: CancelToken | None,
    ) -> tuple[LoaderVersion, ...]:
        if loader_kind == "fabric":
            return fetch_fabric_loader_versions(
                http_client, game_version, endpoints=self.endpoints, cancel_token=cancel_token
            )
        if loader_kind == "forge":
            return fetch_forge_versions(
                http_client, game_version, endpoints=self.endpoints, cancel_token=cancel_token
            )
        if loader_kind == "neoforge":
            return fetch_neoforge_versions(
                http_client, game_version, endpoints=self.endpoints, cancel_token=cancel_token
            )
        message = f"loader {loader_kind!r} không có danh sách bản"
        raise VersionError(message)

    @staticmethod
    def _pick(candidates: tuple[LoaderVersion, ...], loader_version: str | None) -> LoaderVersion:
        if loader_version:
            for candidate in candidates:
                if candidate.loader_version == loader_version:
                    return candidate
            message = f"không có bản loader {loader_version!r}"
            raise VersionError(message)
        return next((c for c in candidates if c.stable), candidates[0])
