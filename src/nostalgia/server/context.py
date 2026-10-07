"""Injected disk, network and account dependencies; one lock serializes server mutations."""

from __future__ import annotations

import threading

from nostalgia.errors import ServerError
from nostalgia.net.http import HttpClient
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.server.catalog import ServerCatalog
from nostalgia.server.content_catalog import ServerContentCatalog
from nostalgia.server.model import DedicatedServer, ServerAccess, ServerGateway, ServerLease
from nostalgia.server.process import ServerProcess
from nostalgia.server.store import ServerStore
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform


class ServerContext:
    def __init__(
        self,
        paths: DataPaths,
        platform: Platform,
        http_client: HttpClient,
        repository: VersionRepository,
        gateway: ServerGateway | None = None,
    ) -> None:
        self.paths, self.platform = paths, platform
        self._http_client, self._repository, self._gateway = http_client, repository, gateway
        self._store = ServerStore(paths.data_dir)
        self._catalog = ServerCatalog(http_client)
        self._content_catalog = ServerContentCatalog(http_client)
        self._lock = threading.RLock()
        self._process: ServerProcess | None = None
        self._lease: ServerLease | None = None
        self._running_id = ""
        self._monitor_stop = threading.Event()
        self._ready = False
        self._active_run = ""
        self._active_port = 0

    def set_gateway(self, gateway: ServerGateway | None) -> None:
        self._gateway = gateway

    def authorize(self) -> ServerAccess:
        if self._gateway is None:
            raise ServerError(
                "Host server đang tạm khoá. Cần dịch vụ tài khoản Google và gói Pro/Max/Ultimate."
            )
        return self._gateway.authorize()

    def list_servers(self) -> tuple[DedicatedServer, ...]:
        return self._store.list_servers()

    def server(self, server_id: str) -> DedicatedServer:
        return self._store.load(server_id)

    def _writable(self, server_id: str) -> None:
        self.authorize()
        self.server(server_id)
        if self._process and self._process.is_running:
            raise ServerError("Dừng server trước khi đổi cấu hình, cài/gỡ plugin hoặc mod.")

    @property
    def running_id(self) -> str:
        return self._running_id if self._process and self._process.is_running else ""

    @property
    def exit_code(self) -> int | None:
        return self._process.exit_code if self._process else None

    @property
    def ready_id(self) -> str:
        return self.running_id if self._ready else ""
