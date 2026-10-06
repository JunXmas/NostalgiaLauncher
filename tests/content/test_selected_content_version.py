"""Bản được chọn phải tải đúng file, giữ phụ thuộc và không tự đổi sang bản mới nhất."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import (
    FABRIC_API,
    JAR,
    SODIUM,
    fabric_target,
    make_content_launcher,
    version_document,
)
from nostalgia.content.model import ContentKind
from nostalgia.errors import ContentError, NetworkError


@pytest.mark.parametrize("content_kind", ["mod", "resourcepack", "shader"])
def test_selected_release_and_replacement(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    content_kind: ContentKind,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    project = launcher.search_content(target, content_kind).hits[0]
    documents = []
    suffix = "jar" if content_kind == "mod" else "zip"
    for version_id in ("new", "old"):
        document = version_document(
            SODIUM,
            loaders=["fabric"],
            deps=[FABRIC_API] if content_kind == "mod" else [],
            url=server.url(f"/cdn/{version_id}.jar"),
        )
        document["id"] = version_id
        document["version_number"] = version_id
        cast(list[dict[str, Any]], document["files"])[0]["filename"] = (
            f"sodium-{version_id}.{suffix}"
        )
        documents.append(document)
        server_state.add(f"/cdn/{version_id}.jar", JAR)
    server_state.add(f"/modrinth/project/{SODIUM}/version", json.dumps(documents).encode())
    report = launcher.install_content(target, project, version_id="old")
    assert report.installed[0].version_id == "old"
    if content_kind == "mod":
        assert report.installed[1].project_id == FABRIC_API
    assert server_state.request_count("/cdn/new.jar") == 0
    assert server_state.request_count("/cdn/old.jar") == 1
    old = next(
        record
        for record in launcher.list_installed_content(target, content_kind)
        if record.project_id == SODIUM
    )
    assert old.version_id == "old"
    launcher.set_content_enabled(target, content_kind, old.file_name, False)
    if content_kind == "resourcepack":
        launcher.update_content(target, launcher.find_content_updates(target, content_kind)[0])
    else:
        launcher.install_content(target, project, version_id="new")
    rows = launcher.list_installed_content(target, content_kind)
    assert [record.file_name for record in rows if record.project_id == SODIUM] == [
        f"sodium-new.{suffix}"
    ]
    directory = (
        target.game_dir
        / {"mod": "mods", "resourcepack": "resourcepacks", "shader": "shaderpacks"}[content_kind]
    )
    assert not (directory / f"sodium-old.{suffix}").exists()
    assert not (directory / f"sodium-old.{suffix}.disabled").exists()


@pytest.mark.parametrize("selected_id", ["missing", "forge", "wrong-game"])
def test_incompatible_selected_release_is_rejected_before_download(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    selected_id: str,
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    project = launcher.search_content(target, "mod").hits[0]
    documents = []
    for version_id, loader_kind, game_version in [
        ("valid", "fabric", VERSION_ID),
        ("forge", "forge", VERSION_ID),
        ("wrong-game", "fabric", "1.20.1"),
    ]:
        document = version_document(
            SODIUM,
            loaders=[loader_kind],
            game_versions=[game_version],
            url=server.url("/cdn/mod.jar"),
        )
        document["id"] = version_id
        documents.append(document)
    server_state.add(f"/modrinth/project/{SODIUM}/version", json.dumps(documents).encode())
    with pytest.raises(ContentError):
        launcher.install_content(target, project, version_id=selected_id)
    assert server_state.request_count("/cdn/mod.jar") == 0
    assert not launcher.list_installed_content(target, "mod")


def test_failed_replacement_keeps_the_installed_mod_and_ledger(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    project = launcher.search_content(target, "mod").hits[0]
    launcher.install_content(target, project)
    before = launcher.list_installed_content(target, "mod")
    document = version_document(SODIUM, loaders=["fabric"], url=server.url("/cdn/broken.jar"))
    document["id"] = "broken"
    cast(list[dict[str, Any]], document["files"])[0]["filename"] = "replacement.jar"
    server_state.add("/cdn/broken.jar", b"x" * len(JAR))
    server_state.add(f"/modrinth/project/{SODIUM}/version", json.dumps([document]).encode())
    with pytest.raises(NetworkError):
        launcher.install_content(target, project, version_id="broken")
    assert launcher.list_installed_content(target, "mod") == before
    assert (target.game_dir / "mods" / f"{SODIUM}.jar").read_bytes() == JAR
    assert not (target.game_dir / "mods" / "replacement.jar").exists()
