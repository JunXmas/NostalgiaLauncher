"""CurseForge, dịch sang cùng hình dạng `content/model.py` như Modrinth.

Hai đường vào, cùng JSON: Worker của dự án (mặc định, khoá ở máy chủ) hoặc api.curseforge.com
thẳng khi người dùng dán khoá riêng ở CÀI ĐẶT. Không dùng proxy của người lạ: không kiểm soát
được, và là chỗ tốt để ai đó chen file lạ vào.
"""

from __future__ import annotations

import json
from urllib.parse import quote, urlencode

from nostalgia.content.model import (
    ContentKind,
    ContentSource,
    Project,
    ProjectVersion,
    SearchPage,
    SortOrder,
)
from nostalgia.errors import ContentError
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints

SOURCE: ContentSource = "curseforge"
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
LOADER_TYPE_BY_NAME = {"forge": 1, "fabric": 4, "quilt": 5, "neoforge": 6}
LOADER_NAME_BY_TYPE = {value: key for key, value in LOADER_TYPE_BY_NAME.items()}
RELEASE_TYPE_NAMES = {1: "release", 2: "beta", 3: "alpha"}
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
        if (project := _parse_project(as_mapping(raw), content_kind)) is not None
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
        if (project_version := _parse_file(as_mapping(raw), endpoints)) is not None
    )
    if not versions:
        message = f"dự án CurseForge {project_id!r} không có file nào tải được"
        raise ContentError(message)
    return versions


def _parse_project(fields: dict[str, JsonValue], content_kind: ContentKind) -> Project | None:
    project_id = as_integer(fields.get("id"))
    title = as_string(fields.get("name"))
    if project_id is None or not title:
        return None
    authors = [
        name
        for raw in as_list(fields.get("authors"))
        if (name := as_string(as_mapping(raw).get("name")))
    ]
    loaders = sorted(
        {
            LOADER_NAME_BY_TYPE[loader_type]
            for raw in as_list(fields.get("latestFilesIndexes"))
            if (loader_type := as_integer(as_mapping(raw).get("modLoader"))) in LOADER_NAME_BY_TYPE
        }
    )
    return Project(
        project_id=str(project_id),
        project_slug=as_string(fields.get("slug")) or str(project_id),
        title=title,
        description=as_string(fields.get("summary")) or "",
        author=", ".join(authors),
        content_kind=content_kind,
        icon_url=as_string(as_mapping(fields.get("logo")).get("thumbnailUrl")) or "",
        downloads=int(as_integer(fields.get("downloadCount")) or 0),
        follows=0,
        loaders=tuple(loaders),
        source=SOURCE,
    )


def _parse_file(fields: dict[str, JsonValue], endpoints: Endpoints) -> ProjectVersion | None:
    file_id = as_integer(fields.get("id"))
    project_id = as_integer(fields.get("modId"))
    file_name = as_string(fields.get("fileName"))
    if file_id is None or project_id is None or not file_name:
        return None
    sha1 = next(
        (
            value
            for raw in as_list(fields.get("hashes"))
            if as_integer(as_mapping(raw).get("algo")) == 1
            and (value := as_string(as_mapping(raw).get("value")))
        ),
        "",
    )
    if not sha1:
        return None
    # CurseForge nhét cả loader lẫn phiên bản game vào một mảng `gameVersions`.
    tags = [text for raw in as_list(fields.get("gameVersions")) if (text := as_string(raw))]
    loaders = tuple(tag.lower() for tag in tags if tag.lower() in LOADER_TYPE_BY_NAME)
    game_versions = tuple(tag for tag in tags if tag[:1].isdigit())
    download_url = as_string(fields.get("downloadUrl")) or cdn_url(endpoints, file_id, file_name)
    required = tuple(
        str(dependency_id)
        for raw in as_list(fields.get("dependencies"))
        if as_integer(as_mapping(raw).get("relationType")) == 3
        and (dependency_id := as_integer(as_mapping(raw).get("modId"))) is not None
    )
    return ProjectVersion(
        version_id=str(file_id),
        project_id=str(project_id),
        version_number=as_string(fields.get("displayName")) or file_name,
        version_type=RELEASE_TYPE_NAMES.get(as_integer(fields.get("releaseType")) or 1, "release"),
        game_versions=game_versions,
        loaders=loaders,
        date_published=as_string(fields.get("fileDate")) or "",
        file_url=download_url,
        file_name=file_name,
        file_sha1=sha1,
        file_size=int(as_integer(fields.get("fileLength")) or 0),
        required_project_ids=required,
    )


def cdn_url(endpoints: Endpoints, file_id: int, file_name: str) -> str:
    """Tên file phải URL-encode: nhiều mod có dấu `+` và CDN trả 403 nếu để nguyên."""
    return f"{endpoints.curseforge_cdn}/{file_id // 1000}/{file_id % 1000}/{quote(file_name)}"


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
