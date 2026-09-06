"""Đọc .mrpack: chỉ mục, loader, bỏ file server-only, chặn host lạ và đường dẫn thoát, overrides."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from nostalgia.content.mrpack import apply_overrides, plan_downloads, read_index
from nostalgia.errors import ContentError, UnsafePathError

CDN = "https://cdn.modrinth.com/data/AANobbMI/versions/x/sodium.jar"


def make_mrpack(
    path: Path,
    *,
    files: list[dict[str, object]],
    dependencies: dict[str, str],
    overrides: dict[str, bytes] | None = None,
) -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "modrinth.index.json",
            json.dumps(
                {
                    "formatVersion": 1,
                    "name": "Goi Vui",
                    "dependencies": dependencies,
                    "files": files,
                }
            ),
        )
        for name, body in (overrides or {}).items():
            archive.writestr(name, body)
    path.write_bytes(buffer.getvalue())
    return path


def sodium(**extra: object) -> dict[str, object]:
    return {
        "path": "mods/sodium.jar",
        "downloads": [CDN],
        "hashes": {"sha1": "a" * 40},
        "fileSize": 10,
        **extra,
    }


def test_index_reads_loader_and_skips_server_only_files(tmp_path: Path) -> None:
    mrpack = make_mrpack(
        tmp_path / "goi.mrpack",
        files=[sodium(), {**sodium(), "path": "mods/server.jar", "env": {"client": "unsupported"}}],
        dependencies={"minecraft": "1.20.1", "fabric-loader": "0.16.9"},
    )
    index = read_index(mrpack)
    assert (index.name, index.game_version, index.loader_kind, index.loader_version) == (
        "Goi Vui",
        "1.20.1",
        "fabric",
        "0.16.9",
    )
    assert [f.relative_path for f in index.files] == ["mods/sodium.jar"]
    tasks = plan_downloads(index, tmp_path / "game")
    assert tasks[0].destination == tmp_path / "game" / "mods" / "sodium.jar"
    assert tasks[0].sha1 == "a" * 40


def test_files_from_unknown_hosts_are_refused(tmp_path: Path) -> None:
    mrpack = make_mrpack(
        tmp_path / "la.mrpack",
        files=[sodium(downloads=["https://evil.example/mod.jar"])],
        dependencies={"minecraft": "1.20.1"},
    )
    with pytest.raises(ContentError, match="host không được phép"):
        read_index(mrpack)


def test_paths_escaping_the_instance_are_refused(tmp_path: Path) -> None:
    mrpack = make_mrpack(
        tmp_path / "thoat.mrpack",
        files=[sodium(path="../../.bashrc")],
        dependencies={"minecraft": "1.20.1"},
    )
    with pytest.raises(UnsafePathError):
        plan_downloads(read_index(mrpack), tmp_path / "game")


def test_overrides_are_copied_and_client_overrides_win(tmp_path: Path) -> None:
    mrpack = make_mrpack(
        tmp_path / "ov.mrpack",
        files=[],
        dependencies={"minecraft": "1.20.1", "neoforge": "21.1.9"},
        overrides={
            "overrides/config/a.toml": b"chung",
            "overrides/options.txt": b"x",
            "client-overrides/config/a.toml": b"client",
        },
    )
    game_dir = tmp_path / "game"
    assert read_index(mrpack).loader_kind == "neoforge"
    assert apply_overrides(mrpack, game_dir) == 3
    assert (game_dir / "config" / "a.toml").read_bytes() == b"client"
    assert (game_dir / "options.txt").read_bytes() == b"x"


def test_quilt_and_broken_archives_are_clear_errors(tmp_path: Path) -> None:
    quilt = make_mrpack(
        tmp_path / "q.mrpack", files=[], dependencies={"minecraft": "1.20.1", "quilt-loader": "0.2"}
    )
    with pytest.raises(ContentError, match="Quilt"):
        read_index(quilt)
    broken = tmp_path / "hong.mrpack"
    broken.write_bytes(b"khong phai zip")
    with pytest.raises(ContentError, match=r"không phải file \.mrpack"):
        read_index(broken)
