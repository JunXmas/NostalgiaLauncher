"""Hangar direct-release plugins; server/platform filters are checked locally."""

from __future__ import annotations

from urllib.parse import quote, urlencode

from nostalgia.errors import ServerError
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import fetch_json
from nostalgia.server.catalog import USER_AGENT
from nostalgia.server.content_model import ServerContentVersion, ServerProject
from nostalgia.server.model import DedicatedServer

HANGAR_URL = "https://hangar.papermc.io/api/v1"


class HangarCatalog:
    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client

    def _fetch(self, url: str) -> JsonValue:
        return fetch_json(
            self._http_client,
            url,
            what="Hangar",
            headers={"User-Agent": USER_AGENT},
            max_bytes=4_000_000,
        )

    def _supported(self, server: DedicatedServer) -> None:
        if server.engine_id not in ("paper", "purpur", "folia"):
            raise ServerError("Hangar hỗ trợ Paper/Purpur/Folia. Hybrid dùng Modrinth.")

    def search(
        self, server: DedicatedServer, query: str, offset: int = 0
    ) -> tuple[ServerProject, ...]:
        self._supported(server)
        parameters = {
            "query": query[:120],
            "platform": "PAPER",
            "limit": 20,
            "offset": max(0, offset),
            "sort": "-downloads",
        }
        rows = as_list(
            as_mapping(self._fetch(HANGAR_URL + "/projects?" + urlencode(parameters))).get("result")
        )
        projects = []
        for row in rows:
            fields = as_mapping(row)
            if server.game_version not in as_list(
                as_mapping(fields.get("supportedPlatforms")).get("PAPER")
            ):
                continue
            if server.engine_id == "folia" and "SUPPORTS_FOLIA" not in as_list(
                as_mapping(fields.get("settings")).get("tags")
            ):
                continue
            namespace = as_mapping(fields.get("namespace"))
            projects.append(
                ServerProject(
                    "hangar",
                    str(namespace.get("owner")) + "/" + str(namespace.get("slug")),
                    str(fields.get("name")),
                    str(fields.get("description")),
                )
            )
        return tuple(projects)

    def versions(
        self, server: DedicatedServer, project_id: str
    ) -> tuple[ServerContentVersion, ...]:
        self._supported(server)
        if not project_id or len(project_id.split("/")) != 2:
            raise ServerError("Mã dự án Hangar không hợp lệ.")
        base_url = (
            HANGAR_URL + "/projects/" + "/".join(quote(p, safe="") for p in project_id.split("/"))
        )
        rows = as_list(
            as_mapping(
                self._fetch(base_url + "/versions?limit=100&platform=PAPER&channel=Release")
            ).get("result")
        )
        versions = []
        for row in rows:
            fields = as_mapping(row)
            if server.game_version not in as_list(
                as_mapping(fields.get("platformDependencies")).get("PAPER")
            ):
                continue
            if str(as_mapping(fields.get("channel")).get("name")).lower() != "release":
                continue
            required = [
                d
                for d in as_list(as_mapping(fields.get("pluginDependencies")).get("PAPER"))
                if as_mapping(d).get("required")
            ]
            if required:
                continue  # External/manual dependencies cannot be installed safely as if bundled.
            remote_file = as_mapping(as_mapping(fields.get("downloads")).get("PAPER"))
            info = as_mapping(remote_file.get("fileInfo"))
            digest = as_string(info.get("sha256Hash")) or ""
            url = as_string(remote_file.get("downloadUrl")) or ""
            if len(digest) == 64 and url and remote_file.get("externalUrl") is None:
                versions.append(
                    ServerContentVersion(
                        "hangar",
                        project_id,
                        str(fields.get("name")),
                        str(fields.get("name")),
                        str(info.get("name")),
                        url,
                        "sha256",
                        digest,
                        as_integer(info.get("sizeBytes")),
                    )
                )
        return tuple(versions)
