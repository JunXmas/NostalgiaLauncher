"""Đọc `.mrpack` của Modrinth: một zip có `modrinth.index.json` và thư mục `overrides/`.

Hai luật an toàn, vì mọi thứ trong file đến từ người lạ:

- **Đường dẫn** (`files[].path`, tên entry trong `overrides/`) đi qua `resolve_within`, nên
  `../../.bashrc` thành lỗi chứ không thành file bị ghi đè. Không bao giờ tạo symlink.
- **URL tải** chỉ được từ các host mà chuẩn mrpack cho phép. Một pack chỉ vào một URL lạ là
  cách rẻ nhất để đẩy một file bất kỳ vào máy người chơi.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.errors import ContentError
from nostalgia.model.download import DownloadTask
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.modloader.model import LoaderKind
from nostalgia.storage.files import ensure_dir, resolve_within

INDEX_FILE_NAME = "modrinth.index.json"
OVERRIDE_PREFIXES = ("overrides/", "client-overrides/")
# Danh sách host của chuẩn mrpack (docs.modrinth.com/docs/modpacks/format_definition).
ALLOWED_HOSTS: tuple[str, ...] = (
    "cdn.modrinth.com",
    "github.com",
    "raw.githubusercontent.com",
    "gitlab.com",
)
LOADER_DEPENDENCY_KEYS: tuple[tuple[str, LoaderKind], ...] = (
    ("fabric-loader", "fabric"),
    ("quilt-loader", "quilt"),
    ("forge", "forge"),
    ("neoforge", "neoforge"),
)


@dataclass(frozen=True, slots=True)
class ModpackFile:
    relative_path: str
    url: str
    sha1: str
    size: int | None


@dataclass(frozen=True, slots=True)
class ModpackIndex:
    name: str
    game_version: str
    loader_kind: LoaderKind
    loader_version: str
    files: tuple[ModpackFile, ...]


def read_index(
    mrpack_path: Path, *, allowed_hosts: tuple[str, ...] = ALLOWED_HOSTS
) -> ModpackIndex:
    """Phân tích chỉ mục; file server-only bị bỏ; host lạ hoặc đường dẫn thoát là lỗi.

    `allowed_hosts` chỉ để test trỏ vào máy chủ cục bộ; sản phẩm luôn dùng danh sách chuẩn.
    """
    try:
        with zipfile.ZipFile(mrpack_path) as archive:
            document: JsonValue = json.loads(archive.read(INDEX_FILE_NAME))
    except (KeyError, zipfile.BadZipFile, ValueError, OSError) as exc:
        message = f"{mrpack_path.name} không phải file .mrpack hợp lệ: {exc}"
        raise ContentError(message) from exc
    fields = as_mapping(document)
    dependencies = as_mapping(fields.get("dependencies"))
    game_version = as_string(dependencies.get("minecraft"))
    if not game_version:
        message = "chỉ mục modpack thiếu dependencies.minecraft"
        raise ContentError(message)
    loader_kind: LoaderKind = "vanilla"
    loader_version = ""
    for key, candidate in LOADER_DEPENDENCY_KEYS:
        if key in dependencies:
            loader_kind = candidate
            loader_version = as_string(dependencies.get(key)) or ""
            break
    files = tuple(
        parsed
        for raw in as_list(fields.get("files"))
        if (parsed := _parse_file(as_mapping(raw), allowed_hosts)) is not None
    )
    return ModpackIndex(
        name=as_string(fields.get("name")) or mrpack_path.stem,
        game_version=game_version,
        loader_kind=loader_kind,
        loader_version=loader_version,
        files=files,
    )


def plan_downloads(index: ModpackIndex, game_dir: Path) -> list[DownloadTask]:
    return [
        DownloadTask(
            url=modpack_file.url,
            destination=resolve_within(game_dir, modpack_file.relative_path),
            sha1=modpack_file.sha1,
            size=modpack_file.size,
        )
        for modpack_file in index.files
    ]


def apply_overrides(mrpack_path: Path, game_dir: Path) -> int:
    """Chép `overrides/` rồi `client-overrides/` (đè lên) vào thư mục bản chơi. Trả số file."""
    written = 0
    with zipfile.ZipFile(mrpack_path) as archive:
        for prefix in OVERRIDE_PREFIXES:
            for member in archive.infolist():
                if not member.filename.startswith(prefix) or member.is_dir():
                    continue
                destination = resolve_within(game_dir, member.filename[len(prefix) :])
                ensure_dir(destination.parent)
                with archive.open(member) as source, destination.open("wb") as target:
                    target.write(source.read())
                written += 1
    return written


def _parse_file(fields: dict[str, JsonValue], allowed_hosts: tuple[str, ...]) -> ModpackFile | None:
    if as_string(as_mapping(fields.get("env")).get("client")) == "unsupported":
        return None
    relative_path = as_string(fields.get("path"))
    urls = [text for raw in as_list(fields.get("downloads")) if (text := as_string(raw))]
    sha1 = as_string(as_mapping(fields.get("hashes")).get("sha1"))
    if not relative_path or not urls or not sha1:
        message = f"file trong modpack thiếu path/downloads/sha1: {fields.get('path')!r}"
        raise ContentError(message)
    url = urls[0]
    host = urlsplit(url).hostname or ""
    if urlsplit(url).scheme != "https" or host not in allowed_hosts:
        message = f"modpack đòi tải từ host không được phép: {url}"
        raise ContentError(message)
    return ModpackFile(
        relative_path=relative_path, url=url, sha1=sha1, size=as_integer(fields.get("size"))
    )
