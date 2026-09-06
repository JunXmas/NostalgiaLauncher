"""Fabric và Quilt: hỏi meta lấy danh sách loader và file profile JSON của một cặp
`game_version` + `loader_version`, rồi lưu profile vào kho version.

Hai loader dùng chung mã vì API cùng hình dạng (meta.fabricmc.net/v2 và meta.quiltmc.org/v3);
chỉ khác địa chỉ và cách đánh dấu bản ổn định (Quilt không có cờ `stable`, nhìn hậu tố
`-beta`). Profile có `inheritsFrom` trỏ về bản Mojang; kho `repo/` đã biết trộn kế thừa, nên
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
    meta_url: str = "",
    loader_label: str = "Fabric",
) -> tuple[LoaderVersion, ...]:
    """Các bản loader dùng được với `game_version`, mới nhất đứng đầu. CHẠM MẠNG.

    `meta_url` trống là Fabric; Quilt truyền `endpoints.quilt_meta` và nhãn của mình.
    """
    url = f"{meta_url or endpoints.fabric_meta}/versions/loader/{game_version}"
    document = _fetch_json(http_client, url, cancel_token)
    versions: list[LoaderVersion] = []
    for candidate in as_list(document):
        loader_fields = as_mapping(as_mapping(candidate).get("loader"))
        loader_version = as_string(loader_fields.get("version"))
        if loader_version:
            stable = loader_fields.get("stable") is True or (
                "stable" not in loader_fields and "-" not in loader_version
            )
            versions.append(LoaderVersion(loader_version=loader_version, stable=stable))
    if not versions:
        message = f"{loader_label} không có bản loader nào cho Minecraft {game_version!r}"
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
    meta_url: str = "",
    loader_label: str = "Fabric",
) -> str:
    """Lưu profile vào kho version và trả về `version_id` của nó. CHẠM MẠNG.

    Không tải thư viện ở đây: đó là việc của `install_version(version_id)` — gọi ngay sau.
    """
    base = meta_url or endpoints.fabric_meta
    url = f"{base}/versions/loader/{game_version}/{loader_version}/profile/json"
    document = _fetch_json(http_client, url, cancel_token)
    if not is_version_document(document):
        message = (
            f"profile {loader_label} cho {game_version} / {loader_version} không phải version JSON"
        )
        raise VersionError(message)
    version_id = as_string(as_mapping(document).get("id"))
    if not version_id:
        message = f"profile {loader_label} thiếu trường `id`"
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
