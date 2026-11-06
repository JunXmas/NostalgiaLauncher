"""Đường dẫn và bản dựng Horizon được ghim theo băm của gói chính thức."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import InstanceError
from nostalgia.storage.paths import DataPaths

HORIZON_GAME_VERSION = "26.3"


@dataclass(frozen=True, slots=True)
class HorizonBuild:
    build_id: str
    build_dir: Path
    game_version: str
    java_major: int
    executable_suffix: str = ""

    @property
    def version_id(self) -> str:
        """Mã riêng khiến launcher cũ từ chối thay vì mở nhầm bằng Java."""
        return f"horizon-{self.game_version}"

    @property
    def game_binary(self) -> Path:
        return self.build_dir / ("horizon-client" + self.executable_suffix)

    @property
    def prepare_binary(self) -> Path:
        return self.build_dir / ("horizon-prepare" + self.executable_suffix)

    @property
    def resources_dir(self) -> Path:
        return self.build_dir.parent / "resources"


def resolve_build_dir(paths: DataPaths, build_id: str) -> Path:
    """Mã lấy từ instance.json cũng phải qua kiểm tra trước khi ghép đường dẫn."""
    if re.fullmatch(r"[0-9a-f]{64}", build_id) is None:
        raise InstanceError("Invalid Horizon build ID; create a Horizon instance first")
    return paths.data_dir / "horizon" / "builds" / build_id / "bundle"
