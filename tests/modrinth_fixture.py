"""Máy chủ Modrinth giả dùng chung cho các test nội dung."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from fake_mojang import VERSION_ID, digest
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import ContentTarget, Instance, Launcher
from test_api import make_launcher

SODIUM = "AANobbMI"
FABRIC_API = "P7dR8mSH"
LOOPER = "loopA"
LOOPEE = "loopB"
JAR = b"noi dung jar" * 5


def version_document(
    project_id: str,
    *,
    loaders: list[str],
    deps: Sequence[str] = (),
    game_versions: list[str] | None = None,
    version_type: str = "release",
    url: str = "",
) -> dict[str, object]:
    return {
        "id": f"{project_id}-v",
        "project_id": project_id,
        "version_number": "1.0",
        "version_type": version_type,
        "game_versions": game_versions or [VERSION_ID],
        "loaders": loaders,
        "date_published": "2026-01-01T00:00:00Z",
        "files": [
            {
                "url": url,
                "filename": f"{project_id}.jar",
                "primary": True,
                "size": len(JAR),
                "hashes": {"sha1": digest(JAR)},
            }
        ],
        "dependencies": [{"project_id": d, "dependency_type": "required"} for d in deps],
    }


def publish_modrinth(server: LocalHttpsServer, state: ServerState) -> None:
    jar_url = server.url(state.add("/cdn/mod.jar", JAR))
    state.add(
        "/modrinth/search",
        json.dumps(
            {
                "hits": [
                    {
                        "project_id": SODIUM,
                        "slug": "sodium",
                        "title": "Sodium",
                        "description": "Nhanh hơn",
                        "author": "jellysquid3",
                        "categories": ["fabric", "optimization"],
                        "icon_url": "",
                        "downloads": 1234,
                        "follows": 56,
                    },
                    {"title": "thiếu id -> bị bỏ"},
                ],
                "offset": 0,
                "total_hits": 41,
            }
        ).encode(),
    )
    versions = {
        SODIUM: [
            version_document(
                SODIUM, loaders=["fabric"], deps=[FABRIC_API], url=jar_url, version_type="beta"
            ),
            version_document(SODIUM, loaders=["fabric"], deps=[FABRIC_API], url=jar_url),
            version_document(SODIUM, loaders=["forge"], url=jar_url),
        ],
        FABRIC_API: [version_document(FABRIC_API, loaders=["fabric"], url=jar_url)],
        LOOPER: [version_document(LOOPER, loaders=["fabric"], deps=[LOOPEE], url=jar_url)],
        LOOPEE: [version_document(LOOPEE, loaders=["fabric"], deps=[LOOPER], url=jar_url)],
    }
    for project_id, documents in versions.items():
        state.add(f"/modrinth/project/{project_id}/version", json.dumps(documents).encode())


def make_content_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> Launcher:
    publish_modrinth(server, server_state)
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    return replace(
        launcher, endpoints=replace(launcher.endpoints, modrinth_api=server.url("/modrinth"))
    )


def fabric_target(launcher: Launcher) -> ContentTarget:
    """Một bản chơi Fabric giả: version JSON kế thừa bản Mojang, mainClass của Fabric."""
    from nostalgia.storage.files import atomic_write_json

    fabric_id = f"fabric-loader-0.16.9-{VERSION_ID}"
    atomic_write_json(
        launcher.paths.version_json(fabric_id),
        {
            "id": fabric_id,
            "inheritsFrom": VERSION_ID,
            "mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient",
        },
    )
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="fab", version_id=fabric_id))
    return launcher.describe_content_target("fab")
