"""Tên/phiên bản mod từ JAR, cache theo mtime/size. Chỉ quét ở worker, không mạng."""

from __future__ import annotations

import json
import re
import tomllib
import zipfile
from pathlib import Path

from nostalgia.content.model import InstalledContent
from nostalgia.errors import ContentError, DataFileError
from nostalgia.modcheck.archive import read_member
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, read_json

CACHE_FILE = ".nostalgia-content-metadata.json"


def load_metadata(directory: Path) -> dict[str, JsonValue]:
    path = directory / CACHE_FILE
    try:
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            return {}
        return as_mapping(read_json(path))
    except (OSError, DataFileError):
        return {}


def cached_labels(raw: JsonValue | None, path: Path) -> tuple[str, str]:
    fields = as_mapping(raw)
    try:
        stamp = path.stat()
    except OSError:
        return "", ""
    if fields.get("mtime") != stamp.st_mtime_ns or fields.get("size") != stamp.st_size:
        return "", ""
    return as_string(fields.get("title")) or "", as_string(fields.get("version")) or ""


def read_labels(path: Path) -> tuple[str, str]:
    try:
        if path.is_symlink() or path.stat().st_size > 512 * 1024 * 1024:
            return "", ""
        with zipfile.ZipFile(path) as archive:
            for member in ("fabric.mod.json", "quilt.mod.json", "mcmod.info"):
                if payload := read_member(archive, member):
                    document: JsonValue = json.loads(payload)
                    if member == "mcmod.info":
                        entries = as_list(document)
                        fields = as_mapping(entries[0]) if entries else as_mapping(document)
                    else:
                        fields = as_mapping(document)
                    if member == "quilt.mod.json":
                        fields = as_mapping(fields.get("quilt_loader"))
                        metadata = as_mapping(fields.get("metadata"))
                    else:
                        metadata = fields
                    return clean(
                        as_string(metadata.get("name"))
                        or as_string(fields.get("id"))
                        or as_string(fields.get("modid"))
                    ), clean(as_string(fields.get("version")))
            for member in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
                if payload := read_member(archive, member):
                    fields = as_mapping(tomllib.loads(payload.decode("utf-8")))
                    entries = as_list(fields.get("mods"))
                    mod = as_mapping(entries[0]) if entries else {}
                    version_number = as_string(mod.get("version")) or ""
                    if version_number == "${file.jarVersion}":
                        manifest = read_member(archive, "META-INF/MANIFEST.MF")
                        match = re.search(rb"(?m)^Implementation-Version:\s*([^\r\n]+)", manifest)
                        version_number = match[1].decode("utf-8") if match else ""
                    return clean(
                        as_string(mod.get("displayName")) or as_string(mod.get("modId"))
                    ), clean(version_number)
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, ContentError):
        pass
    return "", ""


def clean(value: str | None) -> str:
    value = (value or "").strip()
    return "" if value.startswith("${") else value[:256]


def refresh_metadata(directory: Path, installed: tuple[InstalledContent, ...]) -> None:
    previous = load_metadata(directory)
    current: dict[str, JsonValue] = {}
    for installed_content in installed:
        path = directory / (
            installed_content.file_name
            if installed_content.enabled
            else installed_content.file_name + ".disabled"
        )
        try:
            stamp = path.stat()
        except OSError:
            continue
        old = as_mapping(previous.get(installed_content.file_name))
        if old.get("mtime") == stamp.st_mtime_ns and old.get("size") == stamp.st_size:
            current[installed_content.file_name] = old
            continue
        title, version_number = read_labels(path)
        # Do not cache metadata from a file replaced during scanning.
        try:
            current_stamp = path.stat()
            if (current_stamp.st_mtime_ns, current_stamp.st_size) != (
                stamp.st_mtime_ns,
                stamp.st_size,
            ):
                continue
        except OSError:
            continue
        current[installed_content.file_name] = {
            "mtime": stamp.st_mtime_ns,
            "size": stamp.st_size,
            "title": title,
            "version": version_number,
        }
    if current != previous:
        atomic_write_json(directory / CACHE_FILE, current)
