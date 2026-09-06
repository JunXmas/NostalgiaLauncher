"""Fabric: hỏi meta.fabricmc.net lấy danh sách loader và file profile JSON của một cặp
`game_version` + `loader_version`, rồi lưu profile vào kho version.

Profile Fabric có `inheritsFrom` trỏ về bản Mojang; kho `repo/` đã biết trộn kế thừa, nên
sau bước này `install_version(version_id)` và `launch` chạy y như bản thường.
"""

from __future__ import annotations

import json

from nostalgia.errors import VersionError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.modloader.model import LoaderVersion
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints
from nostalgia.repo.version_repo import is_version_document
from nostalgia.storage.files import atomic_write_json
from nostalgia.storage.paths import DataPaths

LOADER_KIND = "fabric"
# Danh sách loader và profile đều là JSON nhỏ; 4 MB là dư mười lần so với thực tế.
MAX_META_BYTES = 4 * 1024 * 1024


def fetch_fabric_loader_versions(
    http_client: HttpClient,
    game_version: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> tuple[LoaderVersion, ...]:
    """Các bản loader dùng được với `game_version`, mới nhất đứng đầu. CHẠM MẠNG."""
    url = f"{endpoints.fabric_meta}/versions/loader/{game_version}"
    document = _fetch_json(http_client, url, cancel_token)
    versions: list[LoaderVersion] = []
    for candidate in as_list(document):
        loader_fields = as_mapping(as_mapping(candidate).get("loader"))
        loader_version = as_string(loader_fields.get("version"))
        if loader_version:
            stable = loader_fields.get("stable") is True
            versions.append(LoaderVersion(loader_version=loader_version, stable=stable))
    if not versions:
        message = f"Fabric không có bản loader nào cho Minecraft {game_version!r}"
        raise VersionError(message)
    return tuple(versions)


def install_fabric_profile(
    http_client: HttpClient,
    paths: DataPaths,
    game_version: str,
    loader_version: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> str:
    """Lưu profile Fabric vào kho version và trả về `version_id` của nó. CHẠM MẠNG.

    Không tải thư viện ở đây: đó là việc của `install_version(version_id)` — gọi ngay sau.
    """
    url = f"{endpoints.fabric_meta}/versions/loader/{game_version}/{loader_version}/profile/json"
    document = _fetch_json(http_client, url, cancel_token)
    if not is_version_document(document):
        message = f"profile Fabric cho {game_version} / {loader_version} không phải version JSON"
        raise VersionError(message)
    version_id = as_string(as_mapping(document).get("id"))
    if not version_id:
        message = "profile Fabric thiếu trường `id`"
        raise VersionError(message)
    atomic_write_json(paths.version_json(version_id), document)
    return version_id


def _fetch_json(http_client: HttpClient, url: str, cancel_token: CancelToken | None) -> JsonValue:
    payload = http_client.fetch_bytes(url, max_bytes=MAX_META_BYTES, cancel_token=cancel_token)
    try:
        parsed: JsonValue = json.loads(payload)
    except ValueError as exc:
        message = f"{url}: phản hồi không phải JSON"
        raise VersionError(message) from exc
    return parsed
