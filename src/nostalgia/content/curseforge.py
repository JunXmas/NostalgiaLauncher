"""CurseForge, dịch sang cùng hình dạng `content/model.py` như Modrinth.

Hai đường vào, cùng JSON: Worker của dự án (mặc định, khoá ở máy chủ) hoặc api.curseforge.com
thẳng khi người dùng dán khoá riêng ở CÀI ĐẶT. Không dùng proxy của người lạ: không kiểm soát
được, và là chỗ tốt để ai đó chen file lạ vào.
"""

from __future__ import annotations

import json
from urllib.parse import quote, urlencode

from nostalgia.content.curseforge_parse import (
    LOADER_TYPE_BY_NAME,
    cdn_url,
    parse_file,
    parse_project,
)
from nostalgia.content.model import ContentKind, ProjectVersion, SearchPage, SortOrder
from nostalgia.errors import ContentError
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints

MINECRAFT_GAME_ID = 432
CLASS_ID_BY_KIND: dict[ContentKind, int] = {
    "mod": 6,
    "resourcepack": 12,
    "shader": 6552,
    "modpack": 4471,
}
# sortField của CurseForge: 1 Featured, 2 Popularity, 3 LastUpdated, 6 TotalDownloads,
# 11 ReleasedDate (mới nhất).
SORT_FIELD_BY_ORDER: dict[SortOrder, int] = {
    "relevance": 2,
    "downloads": 6,
    "follows": 2,
    "newest": 11,
    "updated": 3,
}
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
PAGE_SIZE = 20


def search_projects(
    http_client: HttpClient,
    api_key: str,
    *,
    content_kind: ContentKind,
    query: str = "",
    game_version: str = "",
    loader_kind: str = "",
    sort: SortOrder = "relevance",
    offset: int = 0,
    limit: int = PAGE_SIZE,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> SearchPage:
    """CurseForge chỉ lọc được MỘT phiên bản game và MỘT loader mỗi lần gọi. CHẠM MẠNG."""
    parameters: dict[str, object] = {
        "gameId": MINECRAFT_GAME_ID,
        "classId": CLASS_ID_BY_KIND[content_kind],
        "searchFilter": query,
        "sortField": SORT_FIELD_BY_ORDER[sort],
        "sortOrder": "desc",
        "index": max(offset, 0),
        "pageSize": min(max(limit, 1), 50),
    }
    if game_version:
        parameters["gameVersion"] = game_version
    if content_kind == "mod" and loader_kind in LOADER_TYPE_BY_NAME:
        parameters["modLoaderType"] = LOADER_TYPE_BY_NAME[loader_kind]
    url = f"{_base_url(endpoints, api_key)}/mods/search?{urlencode(parameters)}"
    document = as_mapping(_fetch_json(http_client, api_key, url, cancel_token))
    hits = tuple(
        project
        for raw in as_list(document.get("data"))
        if (project := parse_project(as_mapping(raw), content_kind)) is not None
    )
    pagination = as_mapping(document.get("pagination"))
    return SearchPage(
        hits=hits,
        offset=as_integer(pagination.get("index")) or 0,
        total_hits=as_integer(pagination.get("totalCount")) or len(hits),
    )


def fetch_project_versions(
    http_client: HttpClient,
    api_key: str,
    project_id: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> tuple[ProjectVersion, ...]:
    """Các file của một dự án, mới nhất đứng đầu. CHẠM MẠNG."""
    url = f"{_base_url(endpoints, api_key)}/mods/{quote(project_id, safe='')}/files?pageSize=50"
    document = as_mapping(_fetch_json(http_client, api_key, url, cancel_token))
    versions = tuple(
        project_version
        for raw in as_list(document.get("data"))
        if (project_version := parse_file(as_mapping(raw), endpoints)) is not None
    )
    if not versions:
        message = f"dự án CurseForge {project_id!r} không có file nào tải được"
        raise ContentError(message)
    return versions


def fetch_file(
    http_client: HttpClient,
    api_key: str,
    project_id: str,
    file_id: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> ProjectVersion:
    """Một file cụ thể của một dự án — modpack CurseForge chỉ ghi cặp id này. CHẠM MẠNG."""
    base = _base_url(endpoints, api_key)
    url = f"{base}/mods/{quote(project_id, safe='')}/files/{quote(file_id, safe='')}"
    document = as_mapping(_fetch_json(http_client, api_key, url, cancel_token))
    project_version = parse_file(as_mapping(document.get("data")), endpoints)
    if project_version is None:
        message = f"CurseForge không có file {file_id} của dự án {project_id}, hoặc file thiếu sha1"
        raise ContentError(message)
    return project_version


def _base_url(endpoints: Endpoints, api_key: str) -> str:
    return endpoints.curseforge_direct if api_key.strip() else endpoints.curseforge_proxy


def _fetch_json(
    http_client: HttpClient, api_key: str, url: str, cancel_token: CancelToken | None
) -> JsonValue:
    headers = {"Accept": "application/json"}
    if api_key.strip():
        headers["x-api-key"] = api_key.strip()
    response = http_client.send(
        "GET", url, headers=headers, max_bytes=MAX_RESPONSE_BYTES, cancel_token=cancel_token
    )
    if response.status in (401, 403):
        message = "CurseForge từ chối (401/403): khoá API ở CÀI ĐẶT sai, hoặc máy chủ đang chặn"
        raise ContentError(message)
    if not response.is_ok:
        message = f"CurseForge trả {response.status} cho {url}"
        raise ContentError(message)
    try:
        parsed: JsonValue = json.loads(response.body)
    except ValueError as exc:
        message = f"{url}: phản hồi không phải JSON"
        raise ContentError(message) from exc
    return parsed


__all__ = ["cdn_url", "fetch_file", "fetch_project_versions", "search_projects"]
