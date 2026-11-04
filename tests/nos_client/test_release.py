"""Chọn đúng nhánh Minecraft, bỏ qua artifact không hợp lệ và bản thử nghiệm."""

from __future__ import annotations

import pytest

from nos_fixture import build_nos_jar, build_nos_release
from nostalgia.model.json_value import JsonValue, as_list, as_mapping
from nostalgia.nos_client.compatibility import resolve_nos_game_version
from nostalgia.nos_client.release import parse_mod_releases, resolve_artifact_game_version


@pytest.mark.parametrize(
    ("version_id", "expected"),
    [
        ("fabric-loader-0.19.3-1.21.11", "1.21.11"),
        ("fabric-loader-0.20.1-26.2", None),
        ("fabric-loader-0.20.1-1.8.9", None),
        ("quilt-loader-0.30.0-26.2", None),
        ("26.2", None),
        ("fabric-loader-1.21.11", None),
        ("fabric-loader-../-26.2", None),
    ],
)
def test_resolve_supported_profile(version_id: str, expected: str | None) -> None:
    assert resolve_nos_game_version(version_id) == expected


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("nos-client-0.4.2.jar", "1.21.11"),
        ("nos-client-0.5.0+mc26.2.jar", "26.2"),
        ("nos-client-0.5.1+mc1.21.11.jar", "1.21.11"),
        ("nos-client-0.5.0-sources.jar", None),
        ("nos-client-0.5.0-verification.jar", None),
        ("nos-client-0.5.0+mc1.8.9.jar", "1.8.9"),
        ("../nos-client-0.4.2.jar", None),
    ],
)
def test_artifact_names(file_name: str, expected: str | None) -> None:
    assert resolve_artifact_game_version(file_name) == expected


def test_selects_matching_asset_in_a_mixed_release() -> None:
    body = build_nos_jar()
    legacy = build_nos_release("nos-client-0.4.2.jar", "https://example.test/old.jar", body)
    modern = build_nos_release("nos-client-0.5.0+mc26.2.jar", "https://example.test/new.jar", body)
    document: JsonValue = [modern, legacy]
    assert parse_mod_releases(document, "1.21.11")[0].file_name == "nos-client-0.4.2.jar"
    assert not parse_mod_releases(document, "26.2")


@pytest.mark.parametrize("flag", ["draft", "prerelease"])
def test_unpublished_or_preview_release_is_skipped(flag: str) -> None:
    release = build_nos_release("nos-client-0.4.2.jar", "https://example.test/a.jar", b"jar")
    release[flag] = True
    assert not parse_mod_releases([release], "1.21.11")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "nos-client-../../outside.jar"),
        ("size", True),
        ("size", -1),
        ("size", 100 * 1024 * 1024),
        ("browser_download_url", "http://example.test/a"),
        ("browser_download_url", "https://[invalid"),
        ("digest", "sha256:bad"),
    ],
)
def test_invalid_assets_are_skipped(field: str, value: JsonValue) -> None:
    release = build_nos_release("nos-client-0.4.2.jar", "https://example.test/a.jar", b"jar")
    as_mapping(as_list(release["assets"])[0])[field] = value
    assert not parse_mod_releases([release], "1.21.11")
