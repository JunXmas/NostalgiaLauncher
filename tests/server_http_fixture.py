"""Official HTTP/catalog boundary fixture; production parsing and download logic remain real."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Callable, Mapping
from urllib.parse import parse_qs, urlsplit

from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.operations.cancellation import CancelToken


def jar_bytes(*, folia: bool = True) -> bytes:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nMain-Class: example.Main\n"
        )
        archive.writestr(
            "plugin.yml",
            "name: FixturePlugin\nversion: 1\nfolia-supported: " + str(folia).lower() + "\n",
        )
    return payload.getvalue()


class ServerHttpFixture(HttpClient):
    def __init__(self) -> None:
        self.requests: list[str] = []
        self.payload = jar_bytes()
        self.overrides: dict[str, JsonValue] = {}
        self.corrupt = False

    def send(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int = 8_000_000,
        cancel_token: CancelToken | None = None,
    ) -> HttpResponse:
        self.requests.append(url)
        assert method == "GET" and body is None and max_bytes > 0 and headers
        if cancel_token:
            cancel_token.raise_if_cancelled()
        return HttpResponse(
            200, json.dumps(self.overrides.get(url, self.document(url))).encode(), ()
        )

    def stream(
        self,
        url: str,
        write: Callable[[bytes], None],
        *,
        expected_size: int | None = None,
        max_bytes: int | None = None,
        cancel_token: CancelToken | None = None,
    ) -> int:
        self.requests.append(url)
        assert (expected_size or max_bytes) and url.startswith("https://")
        if cancel_token:
            cancel_token.raise_if_cancelled()
        payload = self.payload + b"corrupt" if self.corrupt else self.payload
        write(payload)
        return len(payload)

    def document(self, url: str) -> JsonValue:
        parts = urlsplit(url)
        digest = hashlib.sha256(self.payload).hexdigest()
        if parts.netloc == "fill.papermc.io":
            if parts.path.endswith("/projects"):
                return {
                    "projects": [
                        {"project": {"id": engine}, "versions": {"1.21": ["1.21.1"]}}
                        for engine in ("paper", "folia")
                    ]
                }
            return [
                {
                    "id": 132,
                    "channel": "STABLE",
                    "downloads": {
                        "server:default": {
                            "url": "https://fill-data.papermc.io/fixture.jar",
                            "size": len(self.payload),
                            "checksums": {"sha256": digest},
                        }
                    },
                }
            ]
        if parts.netloc == "api.purpurmc.org":
            return (
                {"versions": ["1.21.1"]}
                if parts.path.endswith("purpur")
                else {
                    "build": "2300",
                    "result": "SUCCESS",
                    "md5": hashlib.md5(self.payload).hexdigest(),
                }
            )
        if parts.netloc == "meta.fabricmc.net":
            if parts.path.endswith("game"):
                return [{"version": "1.21.1", "stable": True}]
            if parts.path.endswith("installer"):
                return [{"version": "1.0.0", "stable": True}]
            return [{"loader": {"version": "0.16.14", "stable": True}}]
        if parts.netloc == "api.github.com":
            return [
                {
                    "draft": False,
                    "prerelease": False,
                    "assets": [
                        {
                            "name": "arclight-" + engine + "-1.21.1-1.0.1.jar",
                            "size": len(self.payload),
                            "digest": "sha256:" + digest,
                            "browser_download_url": "https://github.com/IzzelAliz/Arclight/fixture.jar",
                        }
                        for engine in ("forge", "neoforge", "fabric")
                    ],
                }
            ]
        if parts.path == "/v2/search":
            return {
                "hits": [
                    {"project_id": project, "title": title, "description": description}
                    for project, title, description in (
                        ("luckperms", "LuckPerms", "Quản lý nhóm và quyền cho người chơi."),
                        ("voice", "Simple Voice Chat", "Trò chuyện bằng giọng nói với bạn bè."),
                        ("chunky", "Chunky", "Tạo trước các vùng thế giới để chơi mượt hơn."),
                    )
                ]
            }
        if parts.netloc == "api.modrinth.com":
            project_id = parts.path.split("/")[3]
            if not parts.path.endswith("/version"):
                return {"project_type": "plugin", "server_side": "required"}
            return [
                {
                    "project_id": project_id,
                    "id": project_id + "-v1",
                    "version_number": "1.0.0",
                    "game_versions": ["1.21.1"],
                    "loaders": ["paper", "bukkit", "spigot", "folia"],
                    "dependencies": [],
                    "files": [
                        {
                            "filename": project_id + ".jar",
                            "primary": True,
                            "size": len(self.payload),
                            "url": "https://cdn.modrinth.com/" + project_id + ".jar",
                            "hashes": {"sha512": hashlib.sha512(self.payload).hexdigest()},
                        }
                    ],
                }
            ]
        if parts.netloc == "hangar.papermc.io":
            return {"result": []}
        raise AssertionError(
            "unexpected server fixture URL " + parts.path + str(parse_qs(parts.query))
        )

    def close(self) -> None:
        """No sockets are owned by this fixture."""
