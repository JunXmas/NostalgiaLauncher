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
from nostalgia.content.modrinth_parse import parse_project, parse_version
from nostalgia.errors import ContentError
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping
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
        if (project := parse_project(as_mapping(raw_hit), content_kind)) is not None
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
        if (project_version := parse_version(as_mapping(raw_version))) is not None
    )
    if not versions:
        message = f"dự án {project_id!r} không có bản phát hành nào có file"
        raise ContentError(message)
    return versions


def lookup_versions_by_hash(
    http_client: HttpClient,
    sha1_hashes: tuple[str, ...],
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> dict[str, ProjectVersion]:
    """Nhận diện file chép tay: sha1 -> bản phát hành trên Modrinth (một request cho cả lô).
    File Modrinth không biết thì không có trong kết quả. CHẠM MẠNG."""
    if not sha1_hashes:
        return {}
    body = json.dumps({"hashes": list(sha1_hashes), "algorithm": "sha1"}).encode()
    document = _fetch_json(
        http_client, f"{endpoints.modrinth_api}/version_files", cancel_token, body=body
    )
    found: dict[str, ProjectVersion] = {}
    for sha1, raw in as_mapping(document).items():
        project_version = parse_version(as_mapping(raw))
        if project_version is not None:
            found[sha1] = project_version
    return found


def fetch_projects(
    http_client: HttpClient,
    project_ids: tuple[str, ...],
    content_kind: ContentKind,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> dict[str, Project]:
    """Tên và icon của nhiều dự án trong một request. CHẠM MẠNG."""
    if not project_ids:
        return {}
    ids = quote(json.dumps(list(project_ids), separators=(",", ":")), safe="")
    document = _fetch_json(
        http_client, f"{endpoints.modrinth_api}/projects?ids={ids}", cancel_token
    )
    projects: dict[str, Project] = {}
    for raw in as_list(document):
        fields = as_mapping(raw)
        # /projects trả `id` thay vì `project_id` như /search.
        project = parse_project({**fields, "project_id": fields.get("id")}, content_kind)
        if project is not None:
            projects[project.project_id] = project
    return projects


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


def _fetch_json(
    http_client: HttpClient,
    url: str,
    cancel_token: CancelToken | None,
    body: bytes | None = None,
) -> JsonValue:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    response = http_client.send(
        "POST" if body is not None else "GET",
        url,
        body=body,
        headers=headers,
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
