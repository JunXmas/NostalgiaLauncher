"""Phân tích bản phát hành: so phiên bản đúng thứ tự, chọn gói theo hệ, đọc SHA256SUMS."""

from __future__ import annotations

from nostalgia.model.json_value import JsonValue
from nostalgia.update.release import (
    LauncherRelease,
    ReleaseAsset,
    bundle_asset_name,
    choose_bundle,
    is_newer,
    parse_release,
    parse_sha256sums,
    parse_version,
)


def test_versions_compare_numerically_and_prereleases_rank_below() -> None:
    assert parse_version("v1.2.3-beta.1") == ((1, 2, 3), ("beta", "1"))
    assert parse_version("0.1") == ((0, 1), ())
    assert parse_version("phiên bản lạ") is None
    assert is_newer("1.2.10", "1.2.9") is True
    assert is_newer("v0.2.0", "0.1.0") is True
    assert is_newer("1.0", "1.0.0") is False
    assert is_newer("1.3.0-beta.1", "1.3.0") is False
    assert is_newer("1.3.0", "1.3.0-beta.1") is True
    assert is_newer("1.3.0-beta.2", "1.3.0-beta.1") is True
    assert is_newer("0.1.0", "0.1.0") is False
    assert is_newer("lạ", "0.1.0") is False, "không đọc được thì không bao giờ tự cài"


def test_github_release_json_becomes_a_release_with_assets() -> None:
    document: JsonValue = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/JunXmas/nostalgia/releases/tag/v0.2.0",
        "body": "Nhật ký game, thông báo, thư viện skin.",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "nostalgia-0.2.0-linux-x64.zip",
                "browser_download_url": "https://x/l.zip",
                "size": 10,
            },
            {
                "name": "nostalgia-0.2.0-windows-x64.zip",
                "browser_download_url": "https://x/w.zip",
                "size": 11,
            },
            {"name": "SHA256SUMS", "browser_download_url": "https://x/SHA256SUMS", "size": 200},
            {"name": "", "browser_download_url": "https://x/rac"},
        ],
    }
    release = parse_release(document)
    assert release is not None
    assert (release.launcher_version, release.prerelease) == ("0.2.0", False)
    assert [release_asset.name for release_asset in release.release_assets] == [
        "nostalgia-0.2.0-linux-x64.zip",
        "nostalgia-0.2.0-windows-x64.zip",
        "SHA256SUMS",
    ]
    assert choose_bundle(release, "linux", "x64") == ReleaseAsset(
        "nostalgia-0.2.0-linux-x64.zip", "https://x/l.zip", 10
    )
    assert choose_bundle(release, "osx", "arm64") is None
    assert bundle_asset_name("0.2.0", "osx", "arm64") == "nostalgia-0.2.0-macos-arm64.zip"
    assert parse_release({"tag_name": "v0.3.0", "draft": True}) is None
    assert parse_release({"message": "Not Found"}) is None


def test_sha256sums_parses_the_sha256sum_format() -> None:
    text = (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        "  nostalgia-0.2.0-linux-x64.zip\n"
        "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
        " *nostalgia-0.2.0-windows-x64.zip\n"
        "dòng rác\n"
    )
    sums = parse_sha256sums(text)
    assert set(sums) == {"nostalgia-0.2.0-linux-x64.zip", "nostalgia-0.2.0-windows-x64.zip"}
    assert sums["nostalgia-0.2.0-windows-x64.zip"].startswith("e3b0c442")
    release = LauncherRelease("0.2.0", "", "", ())
    assert release.asset_named("SHA256SUMS") is None
