"""Dịch JSON của CurseForge sang `content/model.py`. Tách khỏi `curseforge.py` cho file ngắn."""

from __future__ import annotations

from urllib.parse import quote

from nostalgia.content.model import ContentKind, ContentSource, Project, ProjectVersion
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.repo.endpoints import Endpoints

SOURCE: ContentSource = "curseforge"
LOADER_TYPE_BY_NAME = {"forge": 1, "fabric": 4, "quilt": 5, "neoforge": 6}
LOADER_NAME_BY_TYPE = {value: key for key, value in LOADER_TYPE_BY_NAME.items()}
RELEASE_TYPE_NAMES = {1: "release", 2: "beta", 3: "alpha"}


def parse_project(fields: dict[str, JsonValue], content_kind: ContentKind) -> Project | None:
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


def parse_file(fields: dict[str, JsonValue], endpoints: Endpoints) -> ProjectVersion | None:
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
