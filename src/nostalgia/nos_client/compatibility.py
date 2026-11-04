"""Phiên bản game có bản Nos Client tương ứng; dùng chung cho giao diện và lúc chơi."""

from __future__ import annotations

import re

SUPPORTED_GAME_VERSIONS = ("1.21.11",)


def resolve_nos_game_version(version_id: str) -> str | None:
    """Đọc game version từ mã profile Fabric do launcher cài."""
    match = re.fullmatch(r"fabric-loader-[0-9][0-9A-Za-z.+-]*-(1\.21\.11)", version_id)
    return match.group(1) if match else None


def resolve_nos_loader_version(version_id: str) -> str:
    game_version = resolve_nos_game_version(version_id)
    return (
        version_id.removeprefix("fabric-loader-").removesuffix(f"-{game_version}")
        if game_version
        else ""
    )
