"""Modpack CurseForge: đọc manifest, hỏi API từng file, chỉ tải từ CDN CurseForge, overrides."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from curseforge_fixture import FILES_BODY
from fabric_fixture import publish_fabric
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.content.cfpack import read_manifest
from nostalgia.content.model import Project, ProjectVersion
from nostalgia.errors import ContentError
from test_api import make_launcher

PACK_ID = "555"
PACK_FILE_ID = "9001"
MOD_BODY = b"mod tu curseforge" * 5


def make_pack(path: Path, *, loader_id: str = "forge-47.2.0", overrides: str = "overrides") -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "name": "Gói CF",
                    "minecraft": {
                        "version": VERSION_ID,
                        "modLoaders": [{"id": loader_id, "primary": True}],
                    },
                    "files": [
                        {"projectID": 394468, "fileID": 8793729, "required": True},
                        {"projectID": 1, "fileID": 2, "required": False},
                    ],
                    "overrides": overrides,
                }
            ),
        )
        archive.writestr(f"{overrides}/config/cf.toml", b"cau hinh cf")
    path.write_bytes(buffer.getvalue())
    return path


def test_manifest_reads_loader_and_skips_optional_files(tmp_path: Path) -> None:
    manifest = read_manifest(make_pack(tmp_path / "goi.zip"))
    assert (manifest.name, manifest.game_version) == ("Gói CF", VERSION_ID)
    assert (manifest.loader_kind, manifest.loader_version) == ("forge", "47.2.0")
    assert [(f.project_id, f.file_id) for f in manifest.files] == [("394468", "8793729")]
    assert (
        read_manifest(make_pack(tmp_path / "nf.zip", loader_id="neoforge-21.1.9")).loader_kind
        == "neoforge"
    )
    assert (
        read_manifest(make_pack(tmp_path / "fb.zip", loader_id="fabric-0.16.9")).loader_kind
        == "fabric"
    )


def test_broken_archive_is_a_clear_error(tmp_path: Path) -> None:
    broken = tmp_path / "hong.zip"
    broken.write_bytes(b"khong phai zip")
    with pytest.raises(ContentError, match="không phải modpack CurseForge"):
        read_manifest(broken)


def test_files_outside_the_curseforge_cdn_are_refused(tmp_path: Path) -> None:
    from nostalgia.content.cfpack import resolve_files

    manifest = read_manifest(make_pack(tmp_path / "goi.zip"))

    def fetch(_project_id: str, _file_id: str) -> ProjectVersion:
        return ProjectVersion(
            version_id="1",
            project_id="394468",
            version_number="1",
            version_type="release",
            game_versions=(VERSION_ID,),
            loaders=("forge",),
            date_published="",
            file_url="https://evil.example/mod.jar",
            file_name="mod.jar",
            file_sha1="0" * 40,
            file_size=1,
            required_project_ids=(),
        )

    with pytest.raises(ContentError, match="CDN CurseForge"):
        resolve_files(manifest, fetch, tmp_path / "game")


def publish_curseforge_pack(server: LocalHttpsServer, state: ServerState, tmp_path: Path) -> None:
    pack_bytes = make_pack(tmp_path / "goi.zip", loader_id="fabric-0.16.9").read_bytes()
    import hashlib

    pack_url = server.url(state.add("/cdn/9/1/goi.zip", pack_bytes))
    mod_url = server.url(state.add("/cdn/8793/729/sodium+mc26.2.jar", MOD_BODY))
    state.add(
        f"/cf/mods/{PACK_ID}/files",
        json.dumps(
            {
                "data": [
                    {
                        "id": int(PACK_FILE_ID),
                        "modId": int(PACK_ID),
                        "displayName": "Gói CF 1.0",
                        "fileName": "goi.zip",
                        "releaseType": 1,
                        "hashes": [{"value": hashlib.sha1(pack_bytes).hexdigest(), "algo": 1}],
                        "fileDate": "2026-01-01",
                        "fileLength": len(pack_bytes),
                        "downloadUrl": pack_url,
                        "gameVersions": [VERSION_ID, "Fabric"],
                        "dependencies": [],
                    }
                ]
            }
        ).encode(),
    )
    mod_file = dict(FILES_BODY["data"][0])
    mod_file["downloadUrl"] = mod_url
    mod_file["hashes"] = [{"value": hashlib.sha1(MOD_BODY).hexdigest(), "algo": 1}]
    mod_file["fileLength"] = len(MOD_BODY)
    state.add("/cf/mods/394468/files/8793729", json.dumps({"data": mod_file}).encode())


def test_curseforge_modpack_becomes_an_instance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    publish_fabric(server_state)
    publish_curseforge_pack(server, server_state, tmp_path)
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            fabric_meta=server.url("/fabric"),
            curseforge_proxy=server.url("/cf"),
            curseforge_cdn=server.url("/cdn"),
        ),
    )
    pack_bytes = Project(
        project_id=PACK_ID,
        project_slug="goi-cf",
        title="Gói CF",
        description="",
        author="",
        content_kind="modpack",
        icon_url="",
        downloads=0,
        follows=0,
        loaders=("fabric",),
        source="curseforge",
    )

    # Máy chủ giả là localhost: đổi hậu tố host cho phép trong test thì phá luật, nên ở đây
    # trỏ cdn về host giả và nới luật qua tham số của resolve_files bằng monkeypatch nhỏ.
    import nostalgia.content.cfpack as cfpack

    original = cfpack.ALLOWED_HOST_SUFFIXES
    cfpack.ALLOWED_HOST_SUFFIXES = ("localhost",)
    try:
        instance = launcher.install_modpack(pack_bytes, "goi-cf")
    finally:
        cfpack.ALLOWED_HOST_SUFFIXES = original

    assert instance.version_id.startswith("fabric-loader-")
    game_dir = launcher.paths.instance_dir("goi-cf")
    assert (game_dir / "mods" / "sodium+mc26.2.jar").read_bytes() == MOD_BODY
    assert (game_dir / "config" / "cf.toml").read_bytes() == b"cau hinh cf"
    assert server_state.request_count("/cf/mods/394468/files/8793729") == 1
    assert list((launcher.paths.data_dir / "installers").iterdir()) == []
