"""Nguồn bản phát hành và dấu vết file của modpack; không chứa URL do host cung cấp."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PackReference:
    source: Literal["modrinth", "curseforge"]
    project_id: str
    version_id: str
    archive_sha1: str = ""
    title: str = ""


@dataclass(frozen=True, slots=True)
class PackFile:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class PackOrigin:
    reference: PackReference
    game_version: str
    loader_kind: str
    loader_version: str
    files: tuple[PackFile, ...]


@dataclass(frozen=True, slots=True)
class SharedMod:
    relative_path: str
    title: str
    file_name: str
    icon_url: str
    enabled: bool
    shared: bool


@dataclass(frozen=True, slots=True)
class SyncReceipt:
    owner_id: str
    pack_id: str
    instance_id: str
    game_version: str
    loader_kind: str
    loader_version: str
    files: tuple[PackFile, ...]
    excluded_paths: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class SyncChoice:
    relative_path: str
    title: str
    icon_url: str
    content_kind: str
    enabled: bool
    selected: bool
    added: bool


@dataclass(frozen=True, slots=True)
class SyncReview:
    choices: tuple[SyncChoice, ...]
    instance_id: str = ""
    instance_label: str = ""


@dataclass(frozen=True, slots=True)
class SyncPackIdentity:
    owner_id: str = ""
    pack_id: str = ""
