"""Bản phát hành giả trên máy chủ HTTPS cục bộ: gói zip, 302 sang CDN như GitHub, SHA256SUMS,
và một Launcher trỏ vào đó. Dùng chung cho test lõi và test cầu nối cập nhật."""

from __future__ import annotations

import hashlib
import io
import json
import ssl
import zipfile
from dataclasses import replace
from pathlib import Path

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Launcher
from nostalgia.net.http import HttpClient
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform

RELEASE_VERSION = "9.9.9"


def make_bundle(marker: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Nostalgia/nostalgia-ui", "#!/bin/sh\necho " + marker + "\n")
        archive.writestr("Nostalgia/lib/core.txt", marker)
    return buffer.getvalue()


def publish_release(
    server: LocalHttpsServer, state: ServerState, bundle: bytes, *, sums: bool = True
) -> str:
    asset_name = f"nostalgia-{RELEASE_VERSION}-linux-x64.zip"
    # GitHub trả 302 từ browser_download_url sang CDN: máy chủ giả làm y như vậy.
    state.add(f"/cdn/{asset_name}", bundle)
    state.add(f"/download/{asset_name}", b"", status=302, location=server.url(f"/cdn/{asset_name}"))
    release_assets = [
        {
            "name": asset_name,
            "browser_download_url": server.url(f"/download/{asset_name}"),
            "size": len(bundle),
        }
    ]
    if sums:
        digest = hashlib.sha256(bundle).hexdigest()
        state.add("/sums", f"{digest}  {asset_name}\n".encode())
        release_assets.append(
            {"name": "SHA256SUMS", "browser_download_url": server.url("/sums"), "size": 80}
        )
    state.add(
        "/releases/latest",
        json.dumps(
            {
                "tag_name": f"v{RELEASE_VERSION}",
                "html_url": server.url("/page"),
                "body": "Ghi chú",
                "assets": release_assets,
            }
        ).encode(),
    )
    return asset_name


def make_launcher(server: LocalHttpsServer, tmp_path: Path, certificate: Path) -> Launcher:
    trusting = ssl.create_default_context(cafile=str(certificate))
    launcher = Launcher(
        paths=DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config"),
        platform=Platform(os_name="linux", os_arch="x64", os_version="6"),
        make_http_client=lambda: HttpClient(timeout_seconds=5.0, tls_context=trusting),
    )
    return replace(
        launcher,
        endpoints=replace(launcher.endpoints, launcher_releases=server.url("/releases/latest")),
    )
