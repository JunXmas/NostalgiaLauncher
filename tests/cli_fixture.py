"""Đồ dùng chung cho test CLI: ghim đường dẫn vào thư mục tạm, và cài sẵn một bản giả.

Ở gốc `tests/` cùng `fake_mojang.py`: giúp mọi test CLI đi qua đúng một cách ghim thư mục,
nên không test nào lỡ tay chạm vào dữ liệu thật của người dùng.
"""

from __future__ import annotations

from pathlib import Path

from fake_mojang import VERSION_ID, publish
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.launch.runner import install_version
from nostalgia.net.http import HttpClient
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")


def roots(tmp_path: Path) -> list[str]:
    """Đối số ghim cả kho lẫn cấu hình vào thư mục tạm."""
    return ["--data-dir", str(tmp_path / "data"), "--config-dir", str(tmp_path / "config")]


def make_paths(tmp_path: Path) -> DataPaths:
    return DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")


def install_fake_version(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    install_version(
        VERSION_ID,
        http_client,
        make_paths(tmp_path),
        LINUX,
        endpoints=publish(server, server_state),
    )


def fake_java_binary(tmp_path: Path) -> Path:
    """Đường dẫn tới "java" đã cài — trong test nó là một script shell thật."""
    return next(make_paths(tmp_path).runtime_dir.rglob("java"))
