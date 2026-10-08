"""Xác minh byte từ nguồn công khai trước khi dùng bản riêng của host."""

import hashlib

from nostalgia.errors import ContentError, IntegrityError, NetworkError
from nostalgia.facade.modpacks import ModpackOperations
from nostalgia.model.pack import PackReference
from nostalgia.multiplayer.sync_model import SyncFile
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


class SyncDownloadOperations(ModpackOperations):
    __slots__ = ()

    def _fetch_sync_source(
        self,
        http_client: HttpClient,
        source: PackReference,
        sync_file: SyncFile,
        cancel_token: CancelToken,
    ) -> bytes | None:
        try:
            project_version = self.fetch_source_version(http_client, source, cancel_token)
            response = http_client.send(
                "GET", project_version.file_url, max_bytes=sync_file.size, cancel_token=cancel_token
            )
            if (
                response.is_ok
                and len(response.body) == sync_file.size
                and hashlib.sha256(response.body).hexdigest() == sync_file.sha256
            ):
                return response.body
        except (ContentError, NetworkError, IntegrityError):
            pass
        return None
