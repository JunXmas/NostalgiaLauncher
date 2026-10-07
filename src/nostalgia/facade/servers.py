"""The UI requests a domain server manager without knowing storage/catalog/runtime internals."""

from __future__ import annotations

from nostalgia.facade.context import LauncherContext
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.server.manager import ServerManager
from nostalgia.server.model import ServerGateway


class ServerOperations(LauncherContext):
    def make_server_manager(self, gateway: ServerGateway | None = None) -> ServerManager:
        http_client = self.make_http_client()
        repository = VersionRepository(
            self.paths, http_client, manifest_url=self.endpoints.version_manifest
        )
        return ServerManager(self.paths, self.platform, http_client, repository, gateway)
