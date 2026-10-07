"""Domain operations for server settings, content and process ownership."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from nostalgia.errors import ServerError
from nostalgia.operations.cancellation import CancelToken
from nostalgia.server.content_install import install_content, installed_content, remove_content
from nostalgia.server.content_model import (
    InstalledServerContent,
    ServerContentVersion,
    ServerProject,
)
from nostalgia.server.install import ServerInstall
from nostalgia.server.model import DedicatedServer
from nostalgia.server.properties import (
    ServerProperties,
    config_files,
    load_properties,
    read_config,
    save_config,
    save_properties,
)
from nostalgia.server.run import ServerRun


@dataclass(frozen=True, slots=True)
class ServerSelection:
    server: DedicatedServer
    properties: ServerProperties
    installed: tuple[InstalledServerContent, ...]
    config_files: tuple[str, ...]


class ServerManager(ServerInstall, ServerRun):
    def selection(self, server_id: str) -> ServerSelection:
        return ServerSelection(
            self.server(server_id),
            self.properties(server_id),
            self.installed_content(server_id),
            self.config_files(server_id),
        )

    def properties(self, server_id: str) -> ServerProperties:
        return load_properties(self._store.directory(server_id))

    def save_settings(
        self,
        server_id: str,
        properties: ServerProperties,
        heap_megabytes: int,
        java_binary: str = "",
    ) -> None:
        with self._lock:
            self._writable(server_id)
            if not 512 <= heap_megabytes <= 32768:
                raise ServerError("RAM server phải nằm trong khoảng 512-32768 MB.")
            if java_binary and (
                not Path(java_binary).is_file() or any(ord(c) < 32 for c in java_binary)
            ):
                raise ServerError("Đường dẫn Java không hợp lệ. Để trống để dùng Java tự động.")
            server = self.server(server_id)
            save_properties(self._store.directory(server_id), properties)
            self._store.save(
                replace(server, heap_megabytes=heap_megabytes, java_binary=java_binary)
            )

    def directory(self, server_id: str) -> Path:
        self.server(server_id)
        return self._store.directory(server_id)

    def trash(self, server_id: str) -> None:
        with self._lock:
            self._writable(server_id)
            self._store.trash(server_id)

    def search_content(
        self, server_id: str, source: str, content_kind: str, query: str, offset: int = 0
    ) -> tuple[ServerProject, ...]:
        return self._content_catalog.search(
            self.server(server_id), source, content_kind, query, offset
        )

    def content_versions(
        self, server_id: str, source: str, content_kind: str, project_id: str
    ) -> tuple[ServerContentVersion, ...]:
        return self._content_catalog.versions(
            self.server(server_id), source, content_kind, project_id
        )

    def install_content(
        self,
        server_id: str,
        source: str,
        content_kind: str,
        project_id: str,
        version_id: str,
        cancel_token: CancelToken | None = None,
    ) -> None:
        with self._lock:
            self._writable(server_id)
            content_version = next(
                (
                    v
                    for v in self.content_versions(server_id, source, content_kind, project_id)
                    if v.version_id == version_id
                ),
                None,
            )
            if content_version is None:
                raise ServerError("Không có bản plugin/mod tương thích đã chọn.")
            install_content(
                self._http_client,
                self._content_catalog,
                self._store.directory(server_id),
                self.server(server_id),
                content_kind,
                content_version,
                cancel_token,
                self.authorize,
            )

    def installed_content(self, server_id: str) -> tuple[InstalledServerContent, ...]:
        return installed_content(self._store.directory(server_id))

    def remove_content(self, server_id: str, content_kind: str, file_name: str) -> None:
        with self._lock:
            self._writable(server_id)
            remove_content(self._store.directory(server_id), content_kind, file_name)

    def config_files(self, server_id: str) -> tuple[str, ...]:
        return config_files(self._store.directory(server_id))

    def read_config(self, server_id: str, relative_path: str) -> str:
        return read_config(self._store.directory(server_id), relative_path)

    def save_config(self, server_id: str, relative_path: str, text: str) -> None:
        with self._lock:
            self._writable(server_id)
            save_config(self._store.directory(server_id), relative_path, text)
