"""Server content differs from the client library: Bukkit plugins and server-side mods."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServerProject:
    source: str
    project_id: str
    title: str
    description: str
    icon_url: str = ""


@dataclass(frozen=True, slots=True)
class ServerDependency:
    project_id: str = ""
    version_id: str = ""


@dataclass(frozen=True, slots=True)
class ServerContentVersion:
    source: str
    project_id: str
    version_id: str
    title: str
    file_name: str
    url: str
    algorithm: str
    digest: str
    size: int | None = None
    dependencies: tuple[ServerDependency, ...] = ()


@dataclass(frozen=True, slots=True)
class InstalledServerContent:
    source: str
    project_id: str
    version_id: str
    file_name: str
    content_kind: str
    sha256: str
