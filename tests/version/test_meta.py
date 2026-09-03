"""Phân tích JSON phiên bản, trên fixture cắt từ file thật của bốn đời khác nhau."""

from __future__ import annotations

import pytest

from mccore.system.platform_info import Platform
from mccore.version.meta import VersionMeta, parse_version_meta
from mccore.version.rules import rules_allow
from version_fixtures import load_fixture

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")
MACOS = Platform(os_name="osx", os_arch="arm64", os_version="23.5.0")

ALL_VERSIONS = ("1.8.9", "1.12.2", "1.20.1", "1.21.4", "fabric-loader-0.19.3-1.21.4")


def parsed(version_id: str) -> VersionMeta:
    return parse_version_meta(load_fixture(version_id))


@pytest.mark.parametrize("version_id", ALL_VERSIONS)
def test_every_fixture_parses(version_id: str) -> None:
    meta = parsed(version_id)
    assert meta.version_id == version_id
    assert meta.main_class


def test_legacy_versions_use_a_single_argument_string() -> None:
    """Đời ≤1.12: `minecraftArguments` là MỘT CHUỖI, không có rules."""
    meta = parsed("1.8.9")
    assert meta.uses_legacy_arguments is True
    assert meta.minecraft_arguments is not None
    assert "${auth_player_name}" in meta.minecraft_arguments
    assert meta.game_arguments == ()


def test_modern_versions_use_argument_lists() -> None:
    """Đời ≥1.13: danh sách, trong đó phần tử có thể là chuỗi hoặc `{rules, value}`."""
    meta = parsed("1.20.1")
    assert meta.uses_legacy_arguments is False
    assert meta.minecraft_arguments is None
    assert meta.game_arguments and meta.jvm_arguments
    with_rules = [spec for spec in meta.game_arguments if spec.rules]
    assert with_rules, "1.20.1 có tham số phụ thuộc cờ tính năng"


def test_demo_argument_only_applies_with_the_feature_on() -> None:
    meta = parsed("1.20.1")
    demo = next(spec for spec in meta.game_arguments if spec.values == ("--demo",))
    assert rules_allow(demo.rules, LINUX, {"is_demo_user": True}) is True
    assert rules_allow(demo.rules, LINUX) is False


def test_start_on_first_thread_is_macos_only() -> None:
    """LWJGL trên macOS cần cờ này; đưa nó vào lệnh chạy Linux là làm JVM chết."""
    meta = parsed("1.20.1")
    spec = next(s for s in meta.jvm_arguments if "-XstartOnFirstThread" in s.values)
    assert rules_allow(spec.rules, MACOS) is True
    assert rules_allow(spec.rules, LINUX) is False


def test_java_runtime_component_is_read_not_guessed() -> None:
    """Phải tra theo `component`, không phải theo `majorVersion`."""
    expected = {
        "1.8.9": "jre-legacy",
        "1.20.1": "java-runtime-gamma",
        "1.21.4": "java-runtime-delta",
    }
    for version_id, component in expected.items():
        runtime = parsed(version_id).java_runtime
        assert runtime is not None, version_id
        assert runtime.component == component


def test_loader_versions_declare_no_java_runtime() -> None:
    """Bản Fabric không khai gì cả — nó phải lấy từ bản gốc sau khi trộn kế thừa."""
    meta = parsed("fabric-loader-0.19.3-1.21.4")
    assert meta.java_runtime is None
    assert meta.inherits_from == "1.21.4"


def test_asset_index_path_is_relative_to_the_assets_directory() -> None:
    meta = parsed("1.20.1")
    assert meta.asset_index is not None
    assert meta.asset_index.asset_index_id == "5"
    assert meta.asset_index.artifact.relative_path == "indexes/5.json"
    assert meta.asset_index.total_size


def test_client_jar_path_is_relative_to_the_versions_directory() -> None:
    meta = parsed("1.20.1")
    assert meta.client is not None
    assert meta.client.relative_path == "1.20.1/1.20.1.jar"
    assert meta.client.sha1 and meta.client.size


def test_legacy_natives_are_declared_with_a_classifier_map() -> None:
    """Đời ≤1.18: `natives: {linux: "natives-linux"}` cộng `downloads.classifiers`."""
    meta = parsed("1.8.9")
    bundles = [library for library in meta.libraries if library.is_native_bundle]
    assert bundles, "1.8.9 phải có thư viện natives kiểu cũ"
    bundle = bundles[0]
    classifier = bundle.natives_classifier_by_os["linux"]
    assert classifier.startswith("natives-")
    assert classifier in bundle.classifier_artifacts


def test_modern_natives_are_ordinary_libraries_filtered_by_rules() -> None:
    """Đời ≥1.19: natives là thư viện riêng, chọn bằng `rules.os`."""
    meta = parsed("1.20.1")
    assert not any(library.is_native_bundle for library in meta.libraries)
    natives = [
        library
        for library in meta.libraries
        if library.coordinate.classifier and library.coordinate.classifier.startswith("natives-")
    ]
    assert natives
    for library in natives:
        allowed_here = rules_allow(library.rules, LINUX)
        assert allowed_here == (library.coordinate.classifier == "natives-linux")


def test_extract_excludes_are_kept() -> None:
    """`META-INF/` phải bị loại khi giải nén, nếu không jar ký số sẽ làm JVM từ chối nạp."""
    meta = parsed("1.8.9")
    with_excludes = [library for library in meta.libraries if library.extract_excludes]
    assert with_excludes
    assert any("META-INF/" in library.extract_excludes for library in with_excludes)


def test_unknown_top_level_keys_do_not_break_parsing() -> None:
    raw = load_fixture("1.20.1")
    raw["khoaMoiCuaMojang"] = {"gi": [1, 2, 3]}
    assert parse_version_meta(raw).version_id == "1.20.1"


def test_empty_document_parses_to_empty_values() -> None:
    """Không được nổ với dữ liệu rỗng; tầng trên mới là chỗ báo lỗi có ngữ cảnh."""
    meta = parse_version_meta({})
    assert (meta.version_id, meta.main_class) == ("", "")
    assert meta.libraries == ()
