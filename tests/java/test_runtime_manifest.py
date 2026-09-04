"""Phân tích hai tầng manifest bản Java, và chịu được dữ liệu lạ."""

from __future__ import annotations

from java_fixtures import load_catalog_document, load_layout_document
from mccore.java.runtime_manifest import (
    parse_runtime_catalog,
    parse_runtime_layout,
)


def test_catalog_indexes_by_operating_system_and_component() -> None:
    runtime_catalog = parse_runtime_catalog(load_catalog_document())
    release = runtime_catalog.releases["linux", "jre-legacy"]
    assert release.java_component == "jre-legacy"
    assert release.runtime_os_key == "linux"
    assert release.version_name, "tên bản (ví dụ 8u51) cần cho việc báo cho người dùng"
    assert release.manifest.url.startswith("https://")
    assert release.manifest.sha1, "manifest có sha1 — phải giữ để xác minh"


def test_components_declared_but_never_released_are_skipped() -> None:
    """`mac-os-arm64` CÓ khoá `jre-legacy` nhưng danh sách rỗng. Đây là hình dạng thật.

    Nếu coi "có khoá" là "có bản" thì máy Apple Silicon sẽ nhận một bản rỗng và hỏng ở tận
    lúc chạy game, thay vì lùi sang bản Intel ngay từ đầu.
    """
    runtime_catalog = parse_runtime_catalog(load_catalog_document())
    assert ("mac-os-arm64", "jre-legacy") not in runtime_catalog.releases
    assert ("mac-os-arm64", "java-runtime-delta") in runtime_catalog.releases


def test_find_walks_the_fallback_chain_in_order() -> None:
    runtime_catalog = parse_runtime_catalog(load_catalog_document())
    found = runtime_catalog.find("jre-legacy", ("mac-os-arm64", "mac-os"))
    assert found is not None
    assert found.runtime_os_key == "mac-os"

    preferred = runtime_catalog.find("java-runtime-delta", ("mac-os-arm64", "mac-os"))
    assert preferred is not None
    assert preferred.runtime_os_key == "mac-os-arm64", "khoá ưu tiên phải thắng khi có"

    assert runtime_catalog.find("jre-legacy", ("gamecore",)) is None


def test_layout_separates_the_three_entry_kinds() -> None:
    layout = parse_runtime_layout(load_layout_document())
    assert len(layout.directories) == 5
    assert len(layout.files) == 7
    assert layout.links == {
        "bin/ControlPanel": "jcontrol",
        "lib/amd64/server/libjsig.so": "../libjsig.so",
        "man/ja": "ja_JP.UTF-8",
    }


def test_layout_keeps_both_the_raw_and_the_compressed_download() -> None:
    """Sha1 của bản thô là thứ phải khớp SAU khi bung; sha1 bản nén chỉ để xác minh lúc tải."""
    files = {
        runtime_file.relative_path: runtime_file
        for runtime_file in parse_runtime_layout(load_layout_document()).files
    }
    copyright_file = files["COPYRIGHT"]
    assert copyright_file.compressed is not None
    assert copyright_file.compressed.sha1 != copyright_file.raw.sha1
    assert copyright_file.compressed.size is not None
    assert copyright_file.raw.size is not None
    assert copyright_file.compressed.size < copyright_file.raw.size


def test_executable_flag_is_carried_through() -> None:
    files = {f.relative_path: f for f in parse_runtime_layout(load_layout_document()).files}
    assert files["bin/java"].is_executable
    assert not files["COPYRIGHT"].is_executable


def test_malformed_entries_do_not_destroy_the_whole_layout() -> None:
    """Một mục thiếu `url` hay `target` bị bỏ, phần còn lại vẫn dùng được."""
    layout = parse_runtime_layout(
        {
            "files": {
                "tot": {"type": "file", "downloads": {"raw": {"url": "https://a/b", "size": 1}}},
                "thieu-url": {"type": "file", "downloads": {"raw": {"size": 1}}},
                "thieu-target": {"type": "link"},
                "kieu-la": {"type": "socket"},
                "khong-phai-doi-tuong": 5,
            }
        }
    )
    assert [f.relative_path for f in layout.files] == ["tot"]
    assert layout.links == {}
    assert layout.directories == ()


def test_empty_document_parses_to_an_empty_layout() -> None:
    assert parse_runtime_layout(None).files == ()
    assert parse_runtime_catalog(None).releases == {}
