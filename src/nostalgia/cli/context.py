"""Những thứ mọi lệnh con đều cần, dựng một lần ở `main` rồi tiêm xuống.

Không có trạng thái toàn cục và không có đường dẫn mặc định ẩn: đây chính là chỗ luật đó
được thi hành trong thực tế.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform, current_platform


@dataclass(frozen=True, slots=True)
class CliContext:
    """Bối cảnh của một lần gọi lệnh."""

    paths: DataPaths
    platform: Platform
    cancel_token: CancelToken
    quiet: bool = False

    @classmethod
    def build(
        cls,
        *,
        data_dir: str | None,
        config_dir: str | None,
        quiet: bool,
        cancel_token: CancelToken,
    ) -> CliContext:
        platform = current_platform()
        paths = DataPaths.from_env(platform.os_name)
        if data_dir is not None or config_dir is not None:
            paths = DataPaths(
                data_dir=Path(data_dir) if data_dir else paths.data_dir,
                config_dir=Path(config_dir) if config_dir else paths.config_dir,
            )
        return cls(paths=paths, platform=platform, cancel_token=cancel_token, quiet=quiet)
