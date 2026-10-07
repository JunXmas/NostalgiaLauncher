"""Modrinth and Hangar server libraries with exact game and engine compatibility filters."""

from __future__ import annotations

import json
from urllib.parse import quote, urlencode

from nostalgia.errors import ServerError
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import fetch_json
from nostalgia.server.catalog import USER_AGENT
from nostalgia.server.content_model import ServerContentVersion, ServerDependency, ServerProject
from nostalgia.server.hangar_catalog import HangarCatalog
from nostalgia.server.model import DedicatedServer, server_engine

MODRINTH_URL = "https://api.modrinth.com/v2"


class ServerContentCatalog:
    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client

    def _fetch(self, url: str) -> JsonValue:
        return fetch_json(
            self._http_client,
            url,
            what="thư viện nội dung server",
            headers={"User-Agent": USER_AGENT},
            max_bytes=4_000_000,
        )

    def _loaders(self, server: DedicatedServer, content_kind: str) -> tuple[str, ...]:
        engine = server_engine(server.engine_id)
        loaders = (
            engine.plugin_loaders
            if content_kind == "plugin"
            else (engine.mod_loader,)
            if content_kind == "mod"
            else ()
        )
        if not loaders or not all(loaders):
            raise ServerError("Nền tảng server này không hỗ trợ loại nội dung đã chọn.")
        return loaders

    def search(
        self, server: DedicatedServer, source: str, content_kind: str, query: str, offset: int = 0
    ) -> tuple[ServerProject, ...]:
        loaders = self._loaders(server, content_kind)
        if source == "modrinth":
            facets = [
                ["project_type:" + content_kind],
                ["versions:" + server.game_version],
                ["categories:" + loader_fields for loader_fields in loaders],
                ["server_side:required", "server_side:optional"],
            ]
            parameters = {
                "query": query[:120],
                "facets": json.dumps(facets),
                "index": "downloads",
                "limit": 20,
                "offset": max(0, offset),
            }
            rows = as_list(
                as_mapping(self._fetch(MODRINTH_URL + "/search?" + urlencode(parameters))).get(
                    "hits"
                )
            )
            return tuple(
                ServerProject(
                    source,
                    str(as_mapping(row).get("project_id")),
                    str(as_mapping(row).get("title")),
                    str(as_mapping(row).get("description")),
                    as_string(as_mapping(row).get("icon_url")) or "",
                )
                for row in rows
            )
        if source != "hangar" or content_kind != "plugin":
            raise ServerError("Nguồn nội dung server không hợp lệ.")
        return HangarCatalog(self._http_client).search(server, query, offset)

    def versions(
        self, server: DedicatedServer, source: str, content_kind: str, project_id: str
    ) -> tuple[ServerContentVersion, ...]:
        loaders = self._loaders(server, content_kind)
        if source == "modrinth":
            fields = as_mapping(
                self._fetch(MODRINTH_URL + "/project/" + quote(project_id, safe=""))
            )
            project_type = fields.get("project_type")
            legacy_plugin = (
                content_kind == "plugin"
                and project_type == "mod"
                and bool(set(loaders).intersection(as_list(fields.get("loaders"))))
            )
            if (project_type != content_kind and not legacy_plugin) or fields.get(
                "server_side"
            ) == "unsupported":
                raise ServerError("Nội dung này không dành cho server đã chọn.")
            parameters = {
                "loaders": json.dumps(loaders),
                "game_versions": json.dumps([server.game_version]),
            }
            rows = as_list(
                self._fetch(
                    MODRINTH_URL
                    + "/project/"
                    + quote(project_id, safe="")
                    + "/version?"
                    + urlencode(parameters)
                )
            )
            return tuple(
                v
                for row in rows
                if (v := self._modrinth_version(server, content_kind, as_mapping(row))) is not None
            )
        if source != "hangar" or content_kind != "plugin":
            raise ServerError("Nguồn nội dung server không hợp lệ.")
        return HangarCatalog(self._http_client).versions(server, project_id)

    def dependency(
        self, server: DedicatedServer, content_kind: str, dependency: ServerDependency
    ) -> ServerContentVersion:
        if dependency.version_id:
            fields = as_mapping(
                self._fetch(MODRINTH_URL + "/version/" + quote(dependency.version_id, safe=""))
            )
            project_id = as_string(fields.get("project_id")) or ""
            versions = self.versions(server, "modrinth", content_kind, project_id)
            for content_version in versions:
                if content_version.version_id == dependency.version_id:
                    return content_version
        elif dependency.project_id:
            versions = self.versions(server, "modrinth", content_kind, dependency.project_id)
            if versions:
                return versions[0]
        raise ServerError("Không có dependency tương thích với game/loader của server.")

    def _modrinth_version(
        self, server: DedicatedServer, content_kind: str, fields: dict[str, JsonValue]
    ) -> ServerContentVersion | None:
        loaders = self._loaders(server, content_kind)
        if server.game_version not in as_list(fields.get("game_versions")) or not set(
            loaders
        ).intersection(as_list(fields.get("loaders"))):
            return None
        files = [
            as_mapping(f)
            for f in as_list(fields.get("files"))
            if str(as_mapping(f).get("filename")).endswith(".jar")
        ]
        if not files:
            return None
        selected = next((f for f in files if f.get("primary") is True), files[0])
        hashes = as_mapping(selected.get("hashes"))
        algorithm = "sha512" if hashes.get("sha512") else "sha1"
        digest = as_string(hashes.get(algorithm)) or ""
        if len(digest) != (128 if algorithm == "sha512" else 40):
            return None
        dependencies = tuple(
            ServerDependency(
                as_string(as_mapping(d).get("project_id")) or "",
                as_string(as_mapping(d).get("version_id")) or "",
            )
            for d in as_list(fields.get("dependencies"))
            if as_mapping(d).get("dependency_type") == "required"
        )
        return ServerContentVersion(
            "modrinth",
            str(fields.get("project_id")),
            str(fields.get("id")),
            str(fields.get("version_number")),
            str(selected.get("filename")),
            str(selected.get("url")),
            algorithm,
            digest,
            as_integer(selected.get("size")),
            dependencies,
        )
