"""Cài trọn một bản Java từ máy chủ cục bộ: hai tầng manifest, tải, bung, liên kết."""

from __future__ import annotations

import hashlib
import json
import lzma
import stat
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import DataFileError, NetworkError, UnsupportedPlatformError
from nostalgia.java.mojang_jre import ensure_java_runtime, select_runtime_release
from nostalgia.java.runtime_manifest import parse_runtime_catalog
from nostalgia.java.unpack import LZMA_FORMAT
from nostalgia.net.http import HttpClient
from nostalgia.operations.progress import Progress
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.version.meta import JavaRuntimeRef, VersionMeta

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.0")
JAVA_BODY = b"#!/bin/sh\necho openjdk version 1.8.0\n"
LIBRARY_BODY = b"noi dung thu vien\n" * 32
NOTICE_BODY = b"khong nen\n"


def digest(payload: bytes) -> str:
    return hashlib.sha1(payload).hexdigest()


def remote(url: str, payload: bytes) -> dict[str, object]:
    return {"url": url, "sha1": digest(payload), "size": len(payload)}


def publish(
    server: LocalHttpsServer, state: ServerState, *, java_component: str = "jre-legacy"
) -> str:
    """Dựng đủ hai tầng manifest và các file, trả về địa chỉ danh mục.

    Ba file phủ ba đường đi khác nhau: có bản nén và có cờ thực thi, có bản nén thường, và
    không có bản nén.
    """
    files: dict[str, object] = {
        "bin": {"type": "directory"},
        "lib": {"type": "directory"},
        "bin/java": {
            "type": "file",
            "executable": True,
            "downloads": {
                "raw": remote(server.url("/objects/java"), JAVA_BODY),
                "lzma": remote(
                    server.url("/objects/java.lzma"), lzma.compress(JAVA_BODY, format=LZMA_FORMAT)
                ),
            },
        },
        "lib/rt.jar": {
            "type": "file",
            "downloads": {
                "raw": remote(server.url("/objects/rt"), LIBRARY_BODY),
                "lzma": remote(
                    server.url("/objects/rt.lzma"),
                    lzma.compress(LIBRARY_BODY, format=LZMA_FORMAT),
                ),
            },
        },
        "release": {
            "type": "file",
            "downloads": {"raw": remote(server.url("/objects/release"), NOTICE_BODY)},
        },
        "bin/java-cu": {"type": "link", "target": "java"},
    }
    layout = json.dumps({"files": files}).encode()

    state.add("/objects/java.lzma", lzma.compress(JAVA_BODY, format=LZMA_FORMAT))
    state.add("/objects/rt.lzma", lzma.compress(LIBRARY_BODY, format=LZMA_FORMAT))
    state.add("/objects/release", NOTICE_BODY)
    state.add("/runtime.json", layout)
    catalog_document = json.dumps(
        {
            "linux": {
                java_component: [
                    {
                        "manifest": remote(server.url("/runtime.json"), layout),
                        "version": {"name": "8u51"},
                    }
                ]
            }
        }
    ).encode()
    return state.add("/all.json", catalog_document)


def make_paths(tmp_path: Path) -> DataPaths:
    return DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")


def make_version_meta(java_component: str | None = None) -> VersionMeta:
    java_runtime = (
        None
        if java_component is None
        else JavaRuntimeRef(java_component=java_component, major_version=8)
    )
    return VersionMeta(version_id="1.8.9", main_class="Main", java_runtime=java_runtime)


def test_installs_a_complete_runtime(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    catalog_route = publish(server, server_state)
    paths = make_paths(tmp_path)
    steps: list[Progress] = []

    installed_runtime = ensure_java_runtime(
        http_client,
        paths,
        make_version_meta(),
        LINUX,
        on_progress=steps.append,
        catalog_url=server.url(catalog_route),
    )

    runtime_root = paths.java_runtime_dir("jre-legacy", "linux")
    assert installed_runtime.java_binary == runtime_root / "bin" / "java"
    assert installed_runtime.java_component == "jre-legacy"
    assert installed_runtime.runtime_os_key == "linux"
    assert installed_runtime.version_name == "8u51"

    assert installed_runtime.java_binary.read_bytes() == JAVA_BODY
    assert (runtime_root / "lib" / "rt.jar").read_bytes() == LIBRARY_BODY
    assert (runtime_root / "release").read_bytes() == NOTICE_BODY
    assert installed_runtime.java_binary.stat().st_mode & stat.S_IXUSR
    assert (runtime_root / "bin" / "java-cu").is_symlink()
    assert not list(runtime_root.rglob("*.lzma")), "bản nén phải bị xoá sau khi bung"
    assert {step.stage for step in steps} == {"tải", "bung"}


def test_running_twice_downloads_nothing_a_second_time(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """Bản nén bị xoá sau khi bung, nên nếu kế hoạch không kiểm đích thật thì tải lại tất."""
    catalog_route = publish(server, server_state)
    paths = make_paths(tmp_path)
    for _ in range(2):
        ensure_java_runtime(
            http_client, paths, make_version_meta(), LINUX, catalog_url=server.url(catalog_route)
        )

    assert server_state.request_count("/objects/java.lzma") == 1
    assert server_state.request_count("/objects/rt.lzma") == 1
    assert server_state.request_count("/objects/release") == 1
    assert server_state.request_count("/all.json") == 2, "chỉ hai tầng manifest là được đọc lại"


def test_a_platform_mojang_does_not_serve_is_named_in_the_error(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    catalog_route = publish(server, server_state)
    with pytest.raises(UnsupportedPlatformError, match="freebsd"):
        ensure_java_runtime(
            http_client,
            make_paths(tmp_path),
            make_version_meta(),
            Platform(os_name="freebsd", os_arch="x64", os_version="14"),
            catalog_url=server.url(catalog_route),
        )


def test_a_component_never_released_for_this_platform_is_refused(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    catalog_route = publish(server, server_state)
    with pytest.raises(UnsupportedPlatformError, match="java-runtime-delta"):
        ensure_java_runtime(
            http_client,
            make_paths(tmp_path),
            make_version_meta("java-runtime-delta"),
            LINUX,
            catalog_url=server.url(catalog_route),
        )


def test_a_missing_object_fails_loudly_instead_of_half_installing(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """Một bản Java thiếu file thì không chạy — im lặng báo xong là cách hỏng tệ nhất."""
    catalog_route = publish(server, server_state)
    server_state.add("/objects/release", b"", status=404)

    with pytest.raises(NetworkError, match="release"):
        ensure_java_runtime(
            http_client,
            make_paths(tmp_path),
            make_version_meta(),
            LINUX,
            catalog_url=server.url(catalog_route),
        )


def test_a_broken_catalog_names_what_it_was_reading(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    catalog_route = server_state.add("/all.json", b"{khong phai json")
    with pytest.raises(DataFileError, match="danh mục bản Java"):
        ensure_java_runtime(
            http_client,
            make_paths(tmp_path),
            make_version_meta(),
            LINUX,
            catalog_url=server.url(catalog_route),
        )


def test_an_empty_catalog_is_not_silently_accepted(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    catalog_route = server_state.add("/all.json", b"{}")
    with pytest.raises(DataFileError, match="rỗng"):
        ensure_java_runtime(
            http_client,
            make_paths(tmp_path),
            make_version_meta(),
            LINUX,
            catalog_url=server.url(catalog_route),
        )


def test_selection_is_pure_and_needs_no_network() -> None:
    runtime_catalog = parse_runtime_catalog(
        {"linux": {"jre-legacy": [{"manifest": {"url": "https://a"}}]}}
    )
    release = select_runtime_release(runtime_catalog, make_version_meta(), LINUX)
    assert release.runtime_os_key == "linux"
