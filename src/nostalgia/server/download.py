"""Bounded atomic jar downloads with the checksum published by the selected source."""

from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.errors import IntegrityError, ServerError
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken

DOWNLOAD_HOSTS = frozenset(
    (
        "fill-data.papermc.io",
        "api.purpurmc.org",
        "meta.fabricmc.net",
        "github.com",
        "piston-data.mojang.com",
        "launcher.mojang.com",
        "cdn.modrinth.com",
        "hangarcdn.papermc.io",
        "hangar.papermc.io",
    )
)


def download_jar(
    http_client: HttpClient,
    url: str,
    path: Path,
    *,
    algorithm: str = "",
    digest: str = "",
    size: int | None = None,
    cancel_token: CancelToken | None = None,
) -> str:
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname not in DOWNLOAD_HOSTS
        or parts.username
        or parts.password
    ):
        raise ServerError("Bản tải server/plugin phải đến từ nguồn được hỗ trợ qua HTTPS.")
    if size is not None and not 0 < size <= 512 * 1024 * 1024:
        raise ServerError("Bản tải vượt giới hạn 512 MB.")
    if algorithm not in ("", "sha256", "sha512", "sha1", "md5"):
        raise ServerError("Thuật toán kiểm tra bản tải không hợp lệ.")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".download-")
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:

            def write_chunk(payload: bytes) -> None:
                stream.write(payload)

            http_client.stream(
                url,
                write_chunk,
                expected_size=size,
                max_bytes=512 * 1024 * 1024,
                cancel_token=cancel_token,
            )
            stream.flush()
            os.fsync(stream.fileno())
        if algorithm:
            with temporary_path.open("rb") as input_stream:
                actual = hashlib.file_digest(input_stream, algorithm).hexdigest()
            if actual != digest:
                raise IntegrityError("Checksum bản tải server/plugin không khớp nguồn phát hành.")
        with zipfile.ZipFile(temporary_path) as archive:
            if len(archive.infolist()) > 100_000 or not archive.namelist():
                raise ServerError("Bản tải không phải JAR dùng được.")
        with temporary_path.open("rb") as input_stream:
            sha256 = hashlib.file_digest(input_stream, "sha256").hexdigest()
        temporary_path.replace(path)
        return sha256
    except zipfile.BadZipFile as error:
        raise ServerError("Nguồn tải không trả về file JAR hợp lệ.") from error
    finally:
        temporary_path.unlink(missing_ok=True)
