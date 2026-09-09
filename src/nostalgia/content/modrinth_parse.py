"""Dịch JSON của Modrinth sang `content/model.py`. Tách khỏi `modrinth.py` cho file ngắn."""

from __future__ import annotations

from nostalgia.content.model import ContentKind, Project, ProjectVersion
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string


def parse_project(fields: dict[str, JsonValue], content_kind: ContentKind) -> Project | None:
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


def parse_version(fields: dict[str, JsonValue]) -> ProjectVersion | None:
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
        game_versions=strings(fields.get("game_versions")),
        loaders=strings(fields.get("loaders")),
        date_published=as_string(fields.get("date_published")) or "",
        file_url=file_url,
        file_name=file_name,
        file_sha1=file_sha1,
        file_size=as_integer(primary.get("size")) or 0,
        required_project_ids=required,
    )


def strings(value: JsonValue) -> tuple[str, ...]:
    return tuple(text for element in as_list(value) if (text := as_string(element)))
