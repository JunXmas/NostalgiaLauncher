"""Classpath: lọc theo hệ điều hành, bỏ natives, và gộp trùng giữ bản đầu."""

from __future__ import annotations

from pathlib import Path

from nostalgia.install.client import plan_client_task
from nostalgia.model.json_value import JsonValue
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.version.classpath import (
    join_classpath,
    resolve_classpath,
    resolve_classpath_libraries,
)
from nostalgia.version.inherit import resolve_inheritance
from nostalgia.version.meta import VersionMeta, parse_version_meta
from version_fixtures import load_fixture

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")
WINDOWS = Platform(os_name="windows", os_arch="x64", os_version="10.0.22631")
MACOS = Platform(os_name="osx", os_arch="arm64", os_version="23.5.0")
FABRIC_ID = "fabric-loader-0.19.3-1.21.4"


def meta_for(version_id: str) -> VersionMeta:
    return parse_version_meta(load_fixture(version_id))


def test_old_native_bundles_stay_off_the_classpath_but_modern_natives_jars_are_on_it() -> None:
    """Bundle kiểu cũ (≤1.18) mỗi hệ điều hành một file, không lên classpath. Jar natives
    kiểu mới (≥1.19) PHẢI lên classpath: từ 26.x game trỏ java.library.path vào thư mục con
    và trông cậy LWJGL tự bung từ jar — thiếu là "Failed to locate library: liblwjgl.so"."""
    for version_id in ("1.8.9", "1.20.1", "1.21.4"):
        libraries = resolve_classpath_libraries(meta_for(version_id), LINUX)
        assert libraries, version_id
        assert not any(library.is_native_bundle for library in libraries), version_id
    modern = resolve_classpath_libraries(meta_for("1.20.1"), LINUX)
    linux_natives = [str(library.coordinate) for library in modern if library.is_natives_jar]
    assert linux_natives, "1.20.1 khai natives kiểu mới, phải có trên classpath"
    assert all(name.endswith("natives-linux") for name in linux_natives), "chỉ natives của HĐH này"


def test_the_classpath_differs_between_operating_systems() -> None:
    """Kiểm hành vi Windows và macOS ngay khi đang chạy trên Linux."""
    version_meta = meta_for("1.20.1")
    per_os = {
        os_name: {
            str(library.coordinate)
            for library in resolve_classpath_libraries(version_meta, platform)
        }
        for os_name, platform in (("linux", LINUX), ("windows", WINDOWS), ("osx", MACOS))
    }
    assert per_os["linux"] != per_os["windows"] or per_os["linux"] != per_os["osx"]


def duplicate_asm_document() -> dict[str, JsonValue]:
    """Dựng thẳng ca trùng, không dựa vào fixture.

    Fixture đã cắt gọn không chứa ca trùng nào, nên test dựa vào nó là test RỖNG — đã kiểm
    bằng đột biến: bỏ hẳn phần gộp trùng mà không test nào rớt. Dựng thẳng thì ca này luôn
    được đi qua, không phụ thuộc Mojang hay Fabric có tình cờ trùng hay không.
    """
    return {
        "id": "loader-1.21.4",
        "mainClass": "net.fabricmc.Knot",
        "libraries": [
            {"name": "org.ow2.asm:asm:9.10.1"},  # của loader, khai TRƯỚC
            {"name": "com.google.guava:guava:32.1.2-jre"},
            {"name": "org.ow2.asm:asm:9.6"},  # của vanilla, khai SAU
        ],
    }


def test_duplicate_libraries_keep_the_first_version() -> None:
    """Fabric mang `asm 9.10.1` còn vanilla khai `asm 9.6`.

    Thứ tự trộn kế thừa đã đặt loader lên trước, nên giữ bản ĐẦU là giữ bản của loader. Để
    cả hai lên classpath là lỗi "duplicate classes found" mà launcher tiền nhiệm gặp.
    """
    version_meta = parse_version_meta(duplicate_asm_document())
    libraries = resolve_classpath_libraries(version_meta, LINUX)

    coordinates = [str(library.coordinate) for library in libraries]
    assert coordinates == ["org.ow2.asm:asm:9.10.1", "com.google.guava:guava:32.1.2-jre"]

    keys = [library.coordinate.dedupe_key for library in libraries]
    assert len(keys) == len(set(keys))


def test_the_same_artifact_for_two_operating_systems_is_not_a_duplicate() -> None:
    """natives-linux và natives-windows cùng `group:artifact` nhưng là hai thứ khác nhau.

    Gộp nhầm chúng sẽ làm mất natives của một hệ điều hành.
    """
    version_meta = parse_version_meta(
        {
            "id": "x",
            "mainClass": "y",
            "libraries": [
                {"name": "org.lwjgl:lwjgl:3.3.1"},
                {"name": "org.lwjgl:lwjgl:3.3.1:natives-linux"},
                {"name": "org.lwjgl:lwjgl:3.3.1:natives-windows"},
            ],
        }
    )
    keys = {library.coordinate.dedupe_key for library in version_meta.libraries}
    assert len(keys) == 3


def test_order_follows_the_declaration() -> None:
    version_meta = meta_for("1.20.1")
    libraries = resolve_classpath_libraries(version_meta, LINUX)
    declared_order = [
        str(library.coordinate) for library in version_meta.libraries if library.is_classpath_entry
    ]
    assert [str(library.coordinate) for library in libraries] == [
        name for name in declared_order if name in {str(c.coordinate) for c in libraries}
    ]


def test_client_jar_goes_last(tmp_path: Path) -> None:
    """Loader cần lớp của mình được tìm thấy trước lớp của vanilla."""
    version_meta = meta_for("1.20.1")
    paths = DataPaths.for_root(tmp_path)
    classpath = resolve_classpath(version_meta, LINUX, paths)
    assert classpath[-1] == paths.version_jar("1.20.1")
    assert len(classpath) == len(resolve_classpath_libraries(version_meta, LINUX)) + 1


def test_the_classpath_jar_is_the_one_the_downloader_fetches(tmp_path: Path) -> None:
    """Hai chỗ từng tính đường dẫn jar độc lập, và lệch nhau với bản của loader.

    Người gọi rất dễ truyền theo `version_id` vì đó là thứ họ đang cầm, trong khi bản Fabric
    dùng jar của bản gốc. Kết quả: game chạy với classpath trỏ vào file chưa từng được tải.
    """
    paths = DataPaths.for_root(tmp_path)
    version_meta = parse_version_meta(resolve_inheritance(FABRIC_ID, load_fixture))
    downloaded = plan_client_task(version_meta, paths)
    assert downloaded is not None
    assert resolve_classpath(version_meta, LINUX, paths)[-1] == downloaded.destination


def test_paths_follow_the_maven_layout(tmp_path: Path) -> None:
    version_meta = meta_for("1.20.1")
    libraries_dir = DataPaths.for_root(tmp_path).libraries_dir
    classpath = resolve_classpath(version_meta, LINUX, DataPaths.for_root(tmp_path))
    for path in classpath[:-1]:
        assert path.is_relative_to(libraries_dir)
        assert path.suffix == ".jar"


def test_separator_is_per_operating_system(tmp_path: Path) -> None:
    classpath = (tmp_path / "a.jar", tmp_path / "b.jar")
    assert ";" in join_classpath(classpath, "windows")
    assert ":" in join_classpath(classpath, "linux")
    assert ";" not in join_classpath(classpath, "linux")


def test_an_empty_classpath_joins_to_an_empty_string() -> None:
    assert join_classpath((), "linux") == ""
