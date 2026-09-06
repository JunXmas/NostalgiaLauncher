"""Nói chuyện với Modrinth và dịch JSON của họ sang `content/model.py` ngay tại biên.

Chỉ hai endpoint: `/search` và `/project/{id}/project_version`. Không đọc markdown mô tả (không có
chỗ hiển thị an toàn), không đụng CurseForge (cần khoá API hoặc proxy của người lạ).
"""

from __future__ import annotations

import json
from urllib.parse import quote, urlencode

from nostalgia import __version__
from nostalgia.content.model import (
    ContentKind,
    LoaderKind,
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

# Modrinth yêu cầu User-Agent nhận diện được ứng dụng; không có thì bị chặn.
USER_AGENT = f"NostalgiaLauncher/{__version__} (github.com/JunXmas/nostalgia)"
PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def search_projects(
    http_client: HttpClient,
    *,
    content_kind: ContentKind,
    query: str = "",
    game_versions: tuple[str, ...] = (),
    loaders: tuple[str, ...] = (),
    sort: SortOrder = "relevance",
    offset: int = 0,
    limit: int = PAGE_SIZE,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> SearchPage:
    """Một trang kết quả. Facets của Modrinth: các mảng con là AND, phần tử trong một mảng là
    OR — nên nhiều phiên bản / nhiều loader cùng lúc là một mảng. Loader chỉ áp cho mod;
    gói tài nguyên và shader không có loader theo nghĩa này. CHẠM MẠNG."""
    facets: list[list[str]] = [[f"project_type:{content_kind}"]]
    if game_versions:
        facets.append([f"versions:{game_version}" for game_version in game_versions])
    mod_loaders = [loader_name for loader_name in loaders if loader_name != "vanilla"]
    if content_kind == "mod" and mod_loaders:
        facets.append([f"categories:{loader_name}" for loader_name in mod_loaders])
    parameters = {
        "query": query,
        "facets": json.dumps(facets, separators=(",", ":")),
        "index": sort,
        "offset": max(offset, 0),
        "limit": min(max(limit, 1), MAX_PAGE_SIZE),
    }
    url = f"{endpoints.modrinth_api}/search?{urlencode(parameters)}"
    document = as_mapping(_fetch_json(http_client, url, cancel_token))
    hits = tuple(
        project
        for raw_hit in as_list(document.get("hits"))
        if (project := _parse_project(as_mapping(raw_hit), content_kind)) is not None
    )
    return SearchPage(
        hits=hits,
        offset=as_integer(document.get("offset")) or 0,
        total_hits=as_integer(document.get("total_hits")) or len(hits),
    )


def fetch_project_versions(
    http_client: HttpClient,
    project_id: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> tuple[ProjectVersion, ...]:
    """Mọi bản phát hành của một dự án, mới nhất đứng đầu (thứ tự của Modrinth). CHẠM MẠNG.

    Không nhờ máy chủ lọc theo loader/game: lọc ở đây bằng `ProjectVersion.supports` để cùng
    một luật áp cho cả mod lẫn gói tài nguyên, và test kiểm được offline.
    """
    url = f"{endpoints.modrinth_api}/project/{quote(project_id, safe='')}/version"
    document = _fetch_json(http_client, url, cancel_token)
    versions = tuple(
        project_version
        for raw_version in as_list(document)
        if (project_version := _parse_version(as_mapping(raw_version))) is not None
    )
    if not versions:
        message = f"dự án {project_id!r} không có bản phát hành nào có file"
        raise ContentError(message)
    return versions


def choose_version(
    versions: tuple[ProjectVersion, ...],
    *,
    game_version: str,
    loader_kind: LoaderKind,
    content_kind: ContentKind,
) -> ProjectVersion | None:
    """Bản mới nhất tương thích, ưu tiên `release` hơn beta/alpha."""
    compatible = [v for v in versions if v.supports(game_version, loader_kind, content_kind)]
    if not compatible:
        return None
    return next((v for v in compatible if v.version_type == "release"), compatible[0])


def _parse_project(fields: dict[str, JsonValue], content_kind: ContentKind) -> Project | None:
    project_id = as_string(fields.get("project_id"))
    title = as_string(fields.get("title"))
    if not project_id or not title:
        return None
    loaders = tuple(
        name
        for category in as_list(fields.get("categories"))
        if (name := as_string(category)) in ("fabric", "forge", "neoforge", "quilt")
    )
    return Project(
        project_id=project_id,
        project_slug=as_string(fields.get("slug")) or project_id,
        title=title,
        description=as_string(fields.get("description")) or "",
        author=as_string(fields.get("author")) or "",
        content_kind=content_kind,
        icon_url=as_string(fields.get("icon_url")) or "",
        downloads=as_integer(fields.get("downloads")) or 0,
        follows=as_integer(fields.get("follows")) or 0,
        loaders=loaders,
    )


def _parse_version(fields: dict[str, JsonValue]) -> ProjectVersion | None:
    files = [as_mapping(raw_file) for raw_file in as_list(fields.get("files"))]
    primary = next((f for f in files if f.get("primary") is True), files[0] if files else None)
    version_id = as_string(fields.get("id"))
    project_id = as_string(fields.get("project_id"))
    if primary is None or not version_id or not project_id:
        return None
    file_url = as_string(primary.get("url"))
    file_name = as_string(primary.get("filename"))
    file_sha1 = as_string(as_mapping(primary.get("hashes")).get("sha1"))
    if not file_url or not file_name or not file_sha1:
        return None
    required = tuple(
        dependency_project
        for raw_dependency in as_list(fields.get("dependencies"))
        if as_string(as_mapping(raw_dependency).get("dependency_type")) == "required"
        and (dependency_project := as_string(as_mapping(raw_dependency).get("project_id")))
    )
    return ProjectVersion(
        version_id=version_id,
        project_id=project_id,
        version_number=as_string(fields.get("version_number")) or version_id,
        version_type=as_string(fields.get("version_type")) or "release",
        game_versions=_strings(fields.get("game_versions")),
        loaders=_strings(fields.get("loaders")),
        date_published=as_string(fields.get("date_published")) or "",
        file_url=file_url,
        file_name=file_name,
        file_sha1=file_sha1,
        file_size=as_integer(primary.get("size")) or 0,
        required_project_ids=required,
    )


def _strings(value: JsonValue) -> tuple[str, ...]:
    return tuple(text for element in as_list(value) if (text := as_string(element)))


def _fetch_json(http_client: HttpClient, url: str, cancel_token: CancelToken | None) -> JsonValue:
    response = http_client.send(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        max_bytes=MAX_RESPONSE_BYTES,
        cancel_token=cancel_token,
    )
    if not response.is_ok:
        message = f"Modrinth trả {response.status} cho {url}"
        raise ContentError(message)
    try:
        parsed: JsonValue = json.loads(response.body)
    except ValueError as exc:
        message = f"{url}: phản hồi không phải JSON"
        raise ContentError(message) from exc
    return parsed
