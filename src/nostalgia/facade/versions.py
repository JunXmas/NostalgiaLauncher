"""Phiên bản game: liệt kê, cài, Fabric, chẩn đoán."""

from __future__ import annotations

from nostalgia.doctor import Diagnosis, diagnose
from nostalgia.facade.context import LauncherContext
from nostalgia.install.assets import load_installed_asset_index
from nostalgia.launch.runner import InstallReport, install_version, resolve_installed_java_binary
from nostalgia.modloader.fabric import (
    FabricLoaderVersion,
    fetch_fabric_loader_versions,
    install_fabric_profile,
)
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.manifest import ManifestEntry
from nostalgia.repo.version_repo import VersionRepository


class VersionOperations(LauncherContext):
    __slots__ = ()

    def list_installed_versions(self) -> tuple[str, ...]:
        """Các bản đã có trên đĩa. Không chạm mạng."""
        return VersionRepository(self.paths).list_installed()

    def list_released_versions(self, *, limit: int = 50) -> tuple[ManifestEntry, ...]:
        """Danh mục bản chính thức của Mojang. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            manifest = VersionRepository(
                self.paths, http_client, manifest_url=self.endpoints.version_manifest
            ).fetch_manifest()
        return manifest.released()[: max(limit, 0)]

    def install_version(
        self,
        version_id: str,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> InstallReport:
        """Tải đủ một phiên bản. CHẠM MẠNG. Gọi lại khi đã đủ thì gần như không làm gì."""
        with self.make_http_client() as http_client:
            return install_version(
                version_id,
                http_client,
                self.paths,
                self.platform,
                on_progress=on_progress,
                cancel_token=cancel_token,
                endpoints=self.endpoints,
            )

    def list_fabric_loader_versions(self, game_version: str) -> tuple[FabricLoaderVersion, ...]:
        """Các bản Fabric loader cho một phiên bản game, mới nhất đứng đầu. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            return fetch_fabric_loader_versions(http_client, game_version, endpoints=self.endpoints)

    def install_fabric(
        self,
        game_version: str,
        loader_version: str | None = None,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> InstallReport:
        """Cài Fabric cho `game_version`; bỏ trống `loader_version` thì lấy bản ổn định mới
        nhất. CHẠM MẠNG. Trả về báo cáo cài của chính bản Fabric vừa sinh ra."""
        with self.make_http_client() as http_client:
            if loader_version is None:
                candidates = fetch_fabric_loader_versions(
                    http_client, game_version, endpoints=self.endpoints, cancel_token=cancel_token
                )
                loader_version = next(
                    (candidate.loader_version for candidate in candidates if candidate.stable),
                    candidates[0].loader_version,
                )
            version_id = install_fabric_profile(
                http_client,
                self.paths,
                game_version,
                loader_version,
                endpoints=self.endpoints,
                cancel_token=cancel_token,
            )
        return self.install_version(version_id, on_progress=on_progress, cancel_token=cancel_token)

    def diagnose_version(self, version_id: str, *, verify_hashes: bool = False) -> Diagnosis:
        """Soi một bản cài. Không chạm mạng."""
        version_meta = VersionRepository(self.paths).load_version_meta(version_id)
        return diagnose(
            version_meta,
            self.platform,
            self.paths,
            asset_index=load_installed_asset_index(version_meta, self.paths),
            java_binary=resolve_installed_java_binary(version_meta, self.platform, self.paths),
            verify_hashes=verify_hashes,
        )
