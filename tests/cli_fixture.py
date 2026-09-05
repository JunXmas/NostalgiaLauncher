"""Đồ dùng chung cho test CLI: ghim đường dẫn vào thư mục tạm, và cài sẵn một bản giả.

Ở gốc `tests/` cùng `fake_mojang.py`: giúp mọi test CLI đi qua đúng một cách ghim thư mục,
nên không test nào lỡ tay chạm vào dữ liệu thật của người dùng.
"""

from __future__ import annotations

from pathlib import Path

from fake_mojang import VERSION_ID, publish
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.instance.model import Instance
from nostalgia.instance.store import create_instance
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


INSTANCE_ID = "ban-thu"


def create_fake_instance(tmp_path: Path, instance_id: str = INSTANCE_ID) -> None:
    """Tạo bản chơi trỏ vào phiên bản giả — `play` nay nhận bản chơi, không nhận phiên bản."""
    create_instance(make_paths(tmp_path), Instance(instance_id=instance_id, version_id=VERSION_ID))


def install_and_create_instance(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    install_fake_version(server, server_state, http_client, tmp_path)
    create_fake_instance(tmp_path)


def fake_java_binary(tmp_path: Path) -> Path:
    """Đường dẫn tới "java" đã cài — trong test nó là một script shell thật."""
    return next(make_paths(tmp_path).runtime_dir.rglob("java"))
