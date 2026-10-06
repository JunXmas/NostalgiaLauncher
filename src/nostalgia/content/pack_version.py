"""Chọn bản modpack mặc định hoặc bản được người chơi chỉ định."""

from __future__ import annotations

from nostalgia.content.model import ProjectVersion
from nostalgia.errors import ContentError


def choose_pack_version(
    versions: tuple[ProjectVersion, ...],
    game_version: str,
    *,
    project_id: str = "",
    version_id: str = "",
) -> ProjectVersion:
    """Bản chỉ định phải còn tồn tại và hỗ trợ game; không tự rơi về bản khác."""
    if version_id:
        chosen = next(
            (
                release
                for release in versions
                if release.version_id == version_id
                and release.project_id == project_id
                and (not game_version or game_version in release.game_versions)
            ),
            None,
        )
        if chosen is None:
            raise ContentError("selected modpack version is unavailable or incompatible")
        return chosen
    if not versions:
        raise ContentError("modpack has no downloadable versions")
    matching = [release for release in versions if game_version in release.game_versions]
    pool = matching or list(versions)
    return next((release for release in pool if release.version_type == "release"), pool[0])
