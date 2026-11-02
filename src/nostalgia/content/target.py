"""Bản chơi đích của thao tác nội dung, dùng chung giữa các facade."""

from dataclasses import dataclass
from pathlib import Path

from nostalgia.modloader.model import LoaderKind


@dataclass(frozen=True, slots=True)
class ContentTarget:
    instance_id: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind
