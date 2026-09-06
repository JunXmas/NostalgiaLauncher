"""Modpack CurseForge: zip có `manifest.json` (chỉ ghi projectID/fileID) và thư mục overrides.

Khác mrpack, manifest KHÔNG có link tải hay sha1: phải hỏi API từng file. Hai luật an toàn:

- Link tải chỉ được thuộc CDN của CurseForge (`ALLOWED_HOST_SUFFIXES`); API bị chen thì
  cũng không kéo được file từ host lạ vào máy.
- Tên file và manifest_file overrides đi qua `resolve_within`, không bao giờ tạo symlink.
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.content.model import ProjectVersion
from nostalgia.content.pack_files import copy_prefixed_members
from nostalgia.errors import ContentError
from nostalgia.model.download import DownloadTask
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.modloader.model import LoaderKind
from nostalgia.storage.files import resolve_within

MANIFEST_MEMBER = "manifest.json"
ALLOWED_HOST_SUFFIXES: tuple[str, ...] = ("forgecdn.net", "curseforge.com")
RESOLVE_WORKERS = 4
# id modLoaders của manifest: "forge-47.2.0", "fabric-0.16.9", "neoforge-21.1.9", "quilt-0.2".
LOADER_PREFIXES: tuple[tuple[str, LoaderKind], ...] = (
    ("neoforge-", "neoforge"),
    ("forge-", "forge"),
    ("fabric-", "fabric"),
    ("quilt-", "quilt"),
)
FetchFileFn = Callable[[str, str], ProjectVersion]


@dataclass(frozen=True, slots=True)
class ManifestFile:
    project_id: str
    file_id: str


@dataclass(frozen=True, slots=True)
class PackManifest:
    name: str
    game_version: str
    loader_kind: LoaderKind
    loader_version: str
    files: tuple[ManifestFile, ...]
    overrides_prefix: str


def read_manifest(zip_path: Path) -> PackManifest:
    """Phân tích manifest; file `required: false` bị bỏ (là mod tuỳ chọn của pack)."""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            document: JsonValue = json.loads(archive.read(MANIFEST_MEMBER))
    except (KeyError, zipfile.BadZipFile, ValueError, OSError) as exc:
        message = f"{zip_path.name} không phải modpack CurseForge (thiếu manifest.json): {exc}"
        raise ContentError(message) from exc
    fields = as_mapping(document)
    minecraft = as_mapping(fields.get("minecraft"))
    game_version = as_string(minecraft.get("version"))
    if not game_version:
        message = "manifest.json thiếu minecraft.version"
        raise ContentError(message)
    loader_kind: LoaderKind = "vanilla"
    loader_version = ""
    for raw in as_list(minecraft.get("modLoaders")):
        loader_id = (as_string(as_mapping(raw).get("id")) or "").lower()
        for loader_prefix, candidate in LOADER_PREFIXES:
            if loader_id.startswith(loader_prefix):
                loader_kind, loader_version = candidate, loader_id[len(loader_prefix) :]
                break
        if loader_kind != "vanilla":
            break
    files = tuple(
        ManifestFile(project_id=str(project_id), file_id=str(file_id))
        for raw in as_list(fields.get("files"))
        if as_mapping(raw).get("required", True) is not False
        and (project_id := as_integer(as_mapping(raw).get("projectID"))) is not None
        and (file_id := as_integer(as_mapping(raw).get("fileID"))) is not None
    )
    overrides = (as_string(fields.get("overrides")) or "overrides").strip("/") or "overrides"
    return PackManifest(
        name=as_string(fields.get("name")) or zip_path.stem,
        game_version=game_version,
        loader_kind=loader_kind,
        loader_version=loader_version,
        files=files,
        overrides_prefix=overrides,
    )


def resolve_files(
    manifest: PackManifest, fetch_file: FetchFileFn, game_dir: Path
) -> list[DownloadTask]:
    """Hỏi API từng file (song song, giới hạn luồng) và dựng việc tải vào `mods/`."""
    with ThreadPoolExecutor(max_workers=RESOLVE_WORKERS) as pool:
        versions = list(
            pool.map(
                lambda manifest_file: fetch_file(manifest_file.project_id, manifest_file.file_id),
                manifest.files,
            )
        )
    tasks: list[DownloadTask] = []
    for project_version in versions:
        host = urlsplit(project_version.file_url).hostname or ""
        if urlsplit(project_version.file_url).scheme != "https" or not any(
            host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_HOST_SUFFIXES
        ):
            message = f"modpack đòi tải ngoài CDN CurseForge: {project_version.file_url}"
            raise ContentError(message)
        tasks.append(
            DownloadTask(
                url=project_version.file_url,
                destination=resolve_within(game_dir, f"mods/{project_version.file_name}"),
                sha1=project_version.file_sha1,
                size=project_version.file_size or None,
            )
        )
    return tasks


def apply_overrides(zip_path: Path, game_dir: Path, overrides_prefix: str) -> int:
    """Chép thư mục overrides của pack vào thư mục bản chơi. Trả số file."""
    return copy_prefixed_members(zip_path, game_dir, (overrides_prefix,))
