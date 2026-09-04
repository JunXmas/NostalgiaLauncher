"""Phân tích JSON phiên bản, trên fixture cắt từ file thật của bốn đời khác nhau."""

from __future__ import annotations

from pathlib import Path

import pytest

from mccore.model.json_value import as_list
from mccore.storage.paths import DataPaths
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
    version_meta = parsed(version_id)
    assert version_meta.version_id == version_id
    assert version_meta.main_class


def test_legacy_versions_use_a_single_argument_string() -> None:
    """Đời ≤1.12: `minecraftArguments` là MỘT CHUỖI, không có rules."""
    version_meta = parsed("1.8.9")
    assert version_meta.uses_legacy_arguments is True
    assert version_meta.minecraft_arguments is not None
    assert "${auth_player_name}" in version_meta.minecraft_arguments
    assert version_meta.game_arguments == ()


def test_modern_versions_use_argument_lists() -> None:
    """Đời ≥1.13: danh sách, trong đó phần tử có thể là chuỗi hoặc `{rules, value}`."""
    version_meta = parsed("1.20.1")
    assert version_meta.uses_legacy_arguments is False
    assert version_meta.minecraft_arguments is None
    assert version_meta.game_arguments and version_meta.jvm_arguments
    with_rules = [spec for spec in version_meta.game_arguments if spec.rules]
    assert with_rules, "1.20.1 có tham số phụ thuộc cờ tính năng"


def test_demo_argument_only_applies_with_the_feature_on() -> None:
    version_meta = parsed("1.20.1")
    demo = next(spec for spec in version_meta.game_arguments if spec.values == ("--demo",))
    assert rules_allow(demo.rules, LINUX, {"is_demo_user": True}) is True
    assert rules_allow(demo.rules, LINUX) is False


def test_start_on_first_thread_is_macos_only() -> None:
    """LWJGL trên macOS cần cờ này; đưa nó vào lệnh chạy Linux là làm JVM chết."""
    version_meta = parsed("1.20.1")
    spec = next(s for s in version_meta.jvm_arguments if "-XstartOnFirstThread" in s.values)
    assert rules_allow(spec.rules, MACOS) is True
    assert rules_allow(spec.rules, LINUX) is False


def test_java_runtime_component_is_read_not_guessed() -> None:
    """Phải tra theo `java_component`, không phải theo `majorVersion`."""
    expected = {
        "1.8.9": "jre-legacy",
        "1.20.1": "java-runtime-gamma",
        "1.21.4": "java-runtime-delta",
    }
    for version_id, java_component in expected.items():
        java_runtime = parsed(version_id).java_runtime
        assert java_runtime is not None, version_id
        assert java_runtime.java_component == java_component


def test_loader_versions_declare_no_java_runtime() -> None:
    """Bản Fabric không khai gì cả — nó phải lấy từ bản gốc sau khi trộn kế thừa."""
    version_meta = parsed("fabric-loader-0.19.3-1.21.4")
    assert version_meta.java_runtime is None
    assert version_meta.inherits_from == "1.21.4"


def test_asset_index_keeps_only_what_the_server_declared() -> None:
    """Mojang KHÔNG khai đường dẫn cho chỉ mục asset, nên `version_meta` không được tự dựng nó."""
    version_meta = parsed("1.20.1")
    assert version_meta.asset_index is not None
    assert version_meta.asset_index.asset_index_id == "5"
    assert version_meta.asset_index.remote.url.startswith("https://")
    assert version_meta.asset_index.remote.sha1 and version_meta.asset_index.total_size


def test_client_jar_keeps_only_what_the_server_declared() -> None:
    version_meta = parsed("1.20.1")
    assert version_meta.client_jar is not None
    assert version_meta.client_jar.url.startswith("https://")
    assert version_meta.client_jar.sha1 and version_meta.client_jar.size


def test_data_paths_is_the_only_place_that_knows_the_layout(tmp_path: Path) -> None:
    """Trước refactor, `storage/paths.py` và `version/meta.py` cùng biết `indexes/<id>.json`,
    và `DataPaths.asset_index_json` thành hàm không ai gọi. Nay chỉ còn một nguồn."""
    version_meta = parsed("1.20.1")
    paths = DataPaths.for_root(tmp_path)
    assert version_meta.asset_index is not None
    assert version_meta.client_jar is not None

    index_task = version_meta.asset_index.remote.to_task(
        paths.asset_index_json(version_meta.asset_index.asset_index_id)
    )
    jar_task = version_meta.client_jar.to_task(paths.version_jar(version_meta.jar_owner_id))
    assert index_task.destination == paths.assets_dir / "indexes" / "5.json"
    assert jar_task.destination == paths.versions_dir / "1.20.1" / "1.20.1.jar"


def test_libraries_without_a_name_are_skipped() -> None:
    """Trước đây chỗ này truyền `":::"` vào bộ phân tích để khỏi nổ, và một thư viện rỗng
    lọt vào danh sách. Thà thiếu một mục còn hơn mang theo một mục vô nghĩa."""
    raw = load_fixture("1.20.1")
    good = len(parse_version_meta(raw).libraries)
    raw["libraries"] = [*as_list(raw.get("libraries")), {"downloads": {}}, "khong phai dict"]
    assert len(parse_version_meta(raw).libraries) == good


def test_legacy_natives_are_declared_with_a_classifier_map() -> None:
    """Đời ≤1.18: `native_libraries: {linux: "natives-linux"}` cộng `downloads.classifiers`."""
    version_meta = parsed("1.8.9")
    bundles = [library for library in version_meta.libraries if library.is_native_bundle]
    assert bundles, "1.8.9 phải có thư viện native_libraries kiểu cũ"
    bundle = bundles[0]
    classifier = bundle.natives_classifier_by_os["linux"]
    assert classifier.startswith("natives-")
    assert classifier in bundle.classifier_artifacts


def test_modern_natives_are_ordinary_libraries_filtered_by_rules() -> None:
    """Đời ≥1.19: native_libraries là thư viện riêng, chọn bằng `rules.os`."""
    version_meta = parsed("1.20.1")
    assert not any(library.is_native_bundle for library in version_meta.libraries)
    native_libraries = [
        library
        for library in version_meta.libraries
        if library.coordinate.classifier and library.coordinate.classifier.startswith("natives-")
    ]
    assert native_libraries
    for library in native_libraries:
        allowed_here = rules_allow(library.rules, LINUX)
        assert allowed_here == (library.coordinate.classifier == "natives-linux")


def test_extract_excludes_are_kept() -> None:
    """`META-INF/` phải bị loại khi giải nén, nếu không jar ký số sẽ làm JVM từ chối nạp."""
    version_meta = parsed("1.8.9")
    with_excludes = [library for library in version_meta.libraries if library.extract_excludes]
    assert with_excludes
    assert any("META-INF/" in library.extract_excludes for library in with_excludes)


def test_unknown_top_level_keys_do_not_break_parsing() -> None:
    raw = load_fixture("1.20.1")
    raw["khoaMoiCuaMojang"] = {"gi": [1, 2, 3]}
    assert parse_version_meta(raw).version_id == "1.20.1"


def test_empty_document_parses_to_empty_values() -> None:
    """Không được nổ với dữ liệu rỗng; tầng trên mới là chỗ báo lỗi có ngữ cảnh."""
    version_meta = parse_version_meta({})
    assert (version_meta.version_id, version_meta.main_class) == ("", "")
    assert version_meta.libraries == ()
