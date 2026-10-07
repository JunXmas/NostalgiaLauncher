"""Pinned official builds. Catalogs are queried on demand, not at launcher startup."""

from __future__ import annotations

import re
from urllib.parse import quote

from nostalgia.errors import ServerError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import fetch_json
from nostalgia.server.model import ServerArtifact, server_engine
from nostalgia.server.version_order import (
    VERSION_PATTERN,
    sort_game_versions,
    validate_game_version,
)

USER_AGENT = "NostalgiaLauncher/1.2.0 (https://github.com/JunXmas/NostalgiaLauncher)"
PAPER_URL = "https://fill.papermc.io/v3/projects/"
PURPUR_URL = "https://api.purpurmc.org/v2/purpur"
FABRIC_URL = "https://meta.fabricmc.net/v2/versions/"
ARCLIGHT_URL = "https://api.github.com/repos/IzzelAliz/Arclight/releases?per_page=30"
# Verified upstream Mixin bootstrap failure on a clean Java 21 world (2026-10-07).
BROKEN_SHA256 = {"9556a10ca71898e107bd3032616e2ad7ed26998016d080dd19cec5e84d7906eb"}


class ServerCatalog:
    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client

    def _fetch(self, url: str) -> JsonValue:
        return fetch_json(
            self._http_client,
            url,
            what="danh mục server chính thức",
            headers={"User-Agent": USER_AGENT},
            max_bytes=4_000_000,
        )

    def versions(self, engine_id: str) -> tuple[str, ...]:
        server_engine(engine_id)
        if engine_id in ("paper", "folia"):
            projects = as_list(
                as_mapping(self._fetch("https://fill.papermc.io/v3/projects")).get("projects")
            )
            for project in projects:
                fields = as_mapping(project)
                if as_mapping(fields.get("project")).get("id") == engine_id:
                    return sort_game_versions(
                        [
                            v
                            for group in as_mapping(fields.get("versions")).values()
                            for v in as_list(group)
                            if isinstance(v, str)
                        ]
                    )
        if engine_id == "purpur":
            return sort_game_versions(
                [
                    v
                    for v in as_list(as_mapping(self._fetch(PURPUR_URL)).get("versions"))
                    if isinstance(v, str)
                ]
            )
        if engine_id == "fabric":
            return sort_game_versions(
                [
                    str(as_mapping(v).get("version"))
                    for v in as_list(self._fetch(FABRIC_URL + "game"))
                    if as_mapping(v).get("stable") is True
                ]
            )
        if engine_id.startswith("arclight-"):
            return sort_game_versions(
                [artifact.game_version for artifact in self._arclight(engine_id)]
            )
        return ()  # Vanilla versions come from the injected Mojang repository in the façade.

    def builds(self, engine_id: str, game_version: str) -> tuple[ServerArtifact, ...]:
        server_engine(engine_id)
        game_version = validate_game_version(game_version)
        if engine_id in ("paper", "folia"):
            rows = as_list(
                self._fetch(PAPER_URL + engine_id + "/versions/" + game_version + "/builds")
            )
            artifacts = []
            for row in rows:
                fields = as_mapping(row)
                remote_file = as_mapping(as_mapping(fields.get("downloads")).get("server:default"))
                digest = as_string(as_mapping(remote_file.get("checksums")).get("sha256")) or ""
                size = remote_file.get("size")
                channel = fields.get("channel")
                selectable = channel == "STABLE" or (engine_id == "folia" and channel == "ALPHA")
                if selectable and re.fullmatch(r"[a-f0-9]{64}", digest):
                    artifacts.append(
                        ServerArtifact(
                            engine_id,
                            game_version,
                            str(fields.get("id")),
                            str(remote_file.get("url")),
                            "sha256",
                            digest,
                            size if isinstance(size, int) else None,
                        )
                    )
            return tuple(sorted(artifacts, key=lambda a: int(a.build_id), reverse=True))
        if engine_id == "purpur":
            fields = as_mapping(self._fetch(PURPUR_URL + "/" + game_version + "/latest"))
            build_id = as_string(fields.get("build")) or ""
            digest = as_string(fields.get("md5")) or ""
            if (
                fields.get("result") != "SUCCESS"
                or not build_id.isdigit()
                or not re.fullmatch(r"[a-f0-9]{32}", digest)
            ):
                raise ServerError("Không có bản Purpur phát hành dùng được.")
            return (
                ServerArtifact(
                    engine_id,
                    game_version,
                    build_id,
                    PURPUR_URL + "/" + game_version + "/" + build_id + "/download",
                    "md5",
                    digest,
                ),
            )
        if engine_id == "fabric":
            installer = next(
                (
                    as_mapping(row)
                    for row in as_list(self._fetch(FABRIC_URL + "installer"))
                    if as_mapping(row).get("stable") is True
                ),
                {},
            )
            installer_version = quote(as_string(installer.get("version")) or "", safe="")
            if not installer_version:
                raise ServerError("Thiếu Fabric installer chính thức.")
            artifacts = []
            for row in as_list(self._fetch(FABRIC_URL + "loader/" + game_version)):
                loader_fields = as_mapping(as_mapping(row).get("loader"))
                loader_version = as_string(loader_fields.get("version")) or ""
                if loader_fields.get("stable") is True and re.fullmatch(
                    VERSION_PATTERN, loader_version
                ):
                    artifacts.append(
                        ServerArtifact(
                            engine_id,
                            game_version,
                            loader_version,
                            FABRIC_URL
                            + "loader/"
                            + game_version
                            + "/"
                            + loader_version
                            + "/"
                            + installer_version
                            + "/server/jar",
                        )
                    )
            return tuple(artifacts)
        if engine_id.startswith("arclight-"):
            return tuple(a for a in self._arclight(engine_id) if a.game_version == game_version)
        return ()

    def _arclight(self, engine_id: str) -> tuple[ServerArtifact, ...]:
        artifacts = []
        for release in as_list(self._fetch(ARCLIGHT_URL)):
            fields = as_mapping(release)
            if fields.get("draft") or fields.get("prerelease"):
                continue
            for row in as_list(fields.get("assets")):
                asset_fields = as_mapping(row)
                match = re.fullmatch(
                    re.escape(engine_id) + "-(" + VERSION_PATTERN + r")-(.+)\.jar",
                    str(asset_fields.get("name")),
                )
                if match:
                    digest = as_string(asset_fields.get("digest")) or ""
                    if digest.removeprefix("sha256:") in BROKEN_SHA256:
                        continue
                    size = asset_fields.get("size")
                    artifacts.append(
                        ServerArtifact(
                            engine_id,
                            match[1],
                            match[2],
                            str(asset_fields.get("browser_download_url")),
                            "sha256" if digest.startswith("sha256:") else "",
                            digest.removeprefix("sha256:"),
                            size if isinstance(size, int) else None,
                        )
                    )
        return tuple(artifacts)
