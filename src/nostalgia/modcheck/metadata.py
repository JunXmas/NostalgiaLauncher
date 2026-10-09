"""Đọc Fabric/Forge/NeoForge thành bản ghi; không thực thi lớp Java hoặc script trong JAR."""

from __future__ import annotations

import json
import re
import tomllib

from nostalgia.errors import ContentError
from nostalgia.modcheck.model import ModDependency, ModDescriptor
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,96}", value):
        raise ContentError("Metadata có mã mod không hợp lệ.")
    return value


def parse_fabric(payload: bytes) -> tuple[ModDescriptor, ...]:
    fields = as_mapping(json.loads(payload))
    mod_id = identifier(as_string(fields.get("id")) or "")
    version_number = as_string(fields.get("version")) or ""
    dependencies = []
    environment = as_string(fields.get("environment")) or "*"
    if environment not in ("*", "client", "server"):
        raise ContentError("Môi trường mod chưa được hỗ trợ.")
    for section, relationship in (("depends", "required"), ("breaks", "conflict")):
        for target, ranges in as_mapping(fields.get(section)).items():
            predicates = (
                (ranges,)
                if isinstance(ranges, str)
                else tuple(as_string(value) or "" for value in as_list(ranges))
            )
            if not predicates or any(not value or len(value) > 256 for value in predicates):
                raise ContentError("Khoảng phiên bản mod không hợp lệ.")
            dependencies.append(ModDependency(identifier(target), predicates, relationship))
    return (
        ModDescriptor(
            mod_id,
            version_number,
            "fabric",
            tuple(dependencies),
            tuple(identifier(as_string(value) or "") for value in as_list(fields.get("provides"))),
            environment,
        ),
    )


def parse_forge(payload: bytes, manifest: bytes, loader_kind: str) -> tuple[ModDescriptor, ...]:
    fields: JsonValue = tomllib.loads(payload.decode("utf-8"))
    fields = as_mapping(fields)
    descriptors = []
    match = re.search(rb"(?m)^Implementation-Version:\s*([^\r\n]+)", manifest)
    jar_version = match[1].decode("utf-8") if match else ""
    for mod_document in as_list(fields.get("mods")):
        mod_fields = as_mapping(mod_document)
        mod_id = identifier(as_string(mod_fields.get("modId")) or "")
        version_number = as_string(mod_fields.get("version")) or ""
        if version_number == "${file.jarVersion}":
            version_number = jar_version
        dependencies = []
        for dependency_document in as_list(as_mapping(fields.get("dependencies")).get(mod_id)):
            dependency_fields = as_mapping(dependency_document)
            if dependency_fields.get("side") == "SERVER":
                continue
            relationship = (
                "conflict" if dependency_fields.get("type") == "incompatible" else "required"
            )
            if dependency_fields.get("mandatory") is False or dependency_fields.get("type") in (
                "optional",
                "discouraged",
            ):
                continue
            bounds = as_string(dependency_fields.get("versionRange")) or "[0,)"
            if not bounds.startswith(("[", "(")):
                bounds = "[" + bounds + ",)"
            dependencies.append(
                ModDependency(
                    identifier(as_string(dependency_fields.get("modId")) or ""),
                    ("maven:" + bounds,),
                    relationship,
                )
            )
        descriptors.append(ModDescriptor(mod_id, version_number, loader_kind, tuple(dependencies)))
    if not descriptors:
        raise ContentError("Không có mod trong metadata Forge.")
    return tuple(descriptors)
