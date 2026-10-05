"""Nhận diện loader từ mã bản, và bảng tương thích mod (Quilt chạy mod Fabric)."""

from __future__ import annotations

import pytest

from nostalgia.content.model import ProjectVersion
from nostalgia.modloader.model import detect_loader_kind


@pytest.mark.parametrize(
    ("version_id", "expected"),
    [
        ("1.20.1", "vanilla"),
        ("26.2", "vanilla"),
        ("fabric-loader-0.19.5-1.20.1", "fabric"),
        ("quilt-loader-0.29.1-1.20.1", "quilt"),
        ("1.20.1-forge-47.4.10", "forge"),
        ("1.12.2-forge-14.23.5.2860", "forge"),
        ("neoforge-21.1.249", "neoforge"),
        ("1.20.1-neoforge-47.1.3", "neoforge"),
    ],
)
def test_loader_is_read_from_the_version_id(version_id: str, expected: str) -> None:
    assert detect_loader_kind(version_id) == expected


def test_quilt_accepts_fabric_mods_but_forge_does_not() -> None:
    fabric_only = ProjectVersion(
        version_id="v",
        project_id="p",
        version_number="1",
        version_type="release",
        game_versions=("1.20.1",),
        loaders=("fabric",),
        date_published="",
        file_url="u",
        file_name="f.jar",
        file_sha1="0" * 40,
        file_size=1,
        required_project_ids=(),
    )
    assert fabric_only.supports("1.20.1", "quilt", "mod")
    assert fabric_only.supports("1.20.1", "fabric", "mod")
    assert not fabric_only.supports("1.20.1", "forge", "mod")
    assert not fabric_only.supports("1.20.1", "vanilla", "mod")
    assert fabric_only.supports("1.20.1", "vanilla", "resourcepack")
