"""Những gì mọi thao tác của façade cần: đường dẫn, máy, địa chỉ máy chủ, cách mở HTTP."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS, AuthEndpoints
from nostalgia.net.http import HttpClient
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform, current_platform


@dataclass(frozen=True, slots=True)
class LauncherContext:
    """Dựng một lần, tiêm vào; không có đường dẫn mặc định ẩn nào nằm rải trong code."""

    paths: DataPaths
    platform: Platform = field(default_factory=current_platform)
    endpoints: Endpoints = DEFAULT_ENDPOINTS
    auth_endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS
    # Điểm tiêm duy nhất cho phần mạng. Mặc định là bộ khách thật; test trỏ nó sang máy chủ
    # cục bộ, và một ngày nào đó giao diện muốn dùng proxy riêng cũng chỉ cần thay chỗ này.
    make_http_client: Callable[[], HttpClient] = HttpClient

    @classmethod
    def for_environment(cls) -> Self:
        """Dựng theo quy ước thư mục của hệ điều hành đang chạy."""
        platform = current_platform()
        return cls(paths=DataPaths.from_env(platform.os_name), platform=platform)

    @classmethod
    def for_data_dir(cls, data_dir: Path, config_dir: Path | None = None) -> Self:
        """Dựng ở một thư mục chỉ định.

        Có mặt để giao diện **không phải import `DataPaths`**: danh sách module mà giao diện
        được phép chạm càng ngắn thì ranh giới càng khó bị vượt qua vì tiện tay.
        """
        return cls(paths=DataPaths(data_dir=data_dir, config_dir=config_dir or data_dir))
