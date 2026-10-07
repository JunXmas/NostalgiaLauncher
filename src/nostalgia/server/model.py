"""Validated server records and renewable account-service run authorization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from nostalgia.errors import ServerError


@dataclass(frozen=True, slots=True)
class ServerEngine:
    engine_id: str
    title: str
    description: str
    mod_loader: str = ""
    plugin_loaders: tuple[str, ...] = ()


ENGINES = (
    ServerEngine(
        "paper",
        "Paper",
        "Plugin · Phù hợp cho đa số server",
        plugin_loaders=("paper", "spigot", "bukkit"),
    ),
    ServerEngine(
        "purpur",
        "Purpur",
        "Plugin · Nhiều thiết lập gameplay",
        plugin_loaders=("purpur", "paper", "spigot", "bukkit"),
    ),
    ServerEngine(
        "folia",
        "Folia",
        "Plugin · Xử lý nhiều vùng song song; cần plugin hỗ trợ Folia",
        plugin_loaders=("folia",),
    ),
    ServerEngine("fabric", "Fabric", "Mod · Nhẹ, linh hoạt", "fabric"),
    ServerEngine(
        "arclight-forge",
        "Arclight · Forge",
        "Hybrid · Mod Forge + plugin Bukkit/Spigot",
        "forge",
        ("bukkit", "spigot"),
    ),
    ServerEngine(
        "arclight-neoforge",
        "Arclight · NeoForge",
        "Hybrid · Mod NeoForge + plugin Bukkit/Spigot",
        "neoforge",
        ("bukkit", "spigot"),
    ),
    ServerEngine(
        "arclight-fabric",
        "Arclight · Fabric",
        "Hybrid · Mod Fabric + plugin Bukkit/Spigot",
        "fabric",
        ("bukkit", "spigot"),
    ),
    ServerEngine("vanilla", "Vanilla", "Minecraft nguyên bản · Không có mod/plugin"),
)


def server_engine(engine_id: str) -> ServerEngine:
    for engine in ENGINES:
        if engine.engine_id == engine_id:
            return engine
    raise ServerError("Nền tảng server chưa được hỗ trợ.")


@dataclass(frozen=True, slots=True)
class ServerArtifact:
    engine_id: str
    game_version: str
    build_id: str
    url: str
    hash_algorithm: str = ""
    digest: str = ""
    size: int | None = None


@dataclass(frozen=True, slots=True)
class DedicatedServer:
    server_id: str
    display_name: str
    engine_id: str
    game_version: str
    build_id: str
    jar_sha256: str
    heap_megabytes: int = 2048
    java_binary: str = ""


@dataclass(frozen=True, slots=True)
class ServerAccess:
    plan_name: str
    maximum_running: int = 1


@dataclass(frozen=True, slots=True)
class ServerLease:
    server_id: str
    lease_token: str = field(repr=False)
    expires_at: int = 0


@dataclass(frozen=True, slots=True)
class ServerConnection:
    server_id: str
    display_name: str
    port: int


class ServerGateway(Protocol):
    def authorize(self) -> ServerAccess: ...
    def start(self, server_id: str) -> ServerLease: ...
    def renew(self, lease: ServerLease) -> ServerLease: ...
    def release(self, lease: ServerLease) -> None: ...
