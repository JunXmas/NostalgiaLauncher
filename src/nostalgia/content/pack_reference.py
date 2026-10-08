"""Đọc định danh bản phát hành, luôn lấy URL từ API của nguồn tin cậy."""

import re

from nostalgia.model.json_value import JsonValue, as_mapping
from nostalgia.model.pack import PackReference


def parse_pack_reference(document: JsonValue) -> PackReference:
    fields = as_mapping(document)
    source = fields.get("source")
    project_id, version_id = fields.get("project_id"), fields.get("version_id")
    digest, title = fields.get("archive_sha1", ""), fields.get("title", "")
    if (
        source not in ("modrinth", "curseforge")
        or not isinstance(project_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", project_id)
        or not isinstance(version_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", version_id)
        or not isinstance(digest, str)
        or (digest and not re.fullmatch(r"[0-9a-f]{40}", digest))
        or not isinstance(title, str)
        or len(title) > 160
        or any(ord(letter) < 32 for letter in title)
        or (source == "curseforge" and (not project_id.isdigit() or not version_id.isdigit()))
    ):
        raise ValueError("invalid pack reference")
    return PackReference(
        "curseforge" if source == "curseforge" else "modrinth",
        project_id,
        version_id,
        digest,
        title,
    )


def reference_document(reference: PackReference) -> dict[str, JsonValue]:
    return {
        "source": reference.source,
        "project_id": reference.project_id,
        "version_id": reference.version_id,
        "archive_sha1": reference.archive_sha1,
        "title": reference.title,
    }
