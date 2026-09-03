"""Trộn `inheritsFrom` — kể cả chặn vòng tròn, thứ sẽ treo launcher nếu không chặn."""

from __future__ import annotations

import pytest

from mccore.errors import VersionError
from mccore.model.json_value import JsonValue, as_list, as_mapping, as_string
from mccore.version.inherit import MAX_INHERITANCE_DEPTH, merge_inherited, resolve_inheritance
from mccore.version.meta import parse_version_meta
from version_fixtures import load_fixture

FABRIC_ID = "fabric-loader-0.19.3-1.21.4"


def fixture_loader(version_id: str) -> JsonValue:
    return load_fixture(version_id)


def test_fabric_inherits_everything_it_does_not_declare() -> None:
    merged = resolve_inheritance(FABRIC_ID, fixture_loader)
    meta = parse_version_meta(merged)
    assert meta.version_id == FABRIC_ID, "id của bản con thắng"
    assert meta.main_class.startswith("net.fabricmc"), "mainClass của bản con thắng"
    assert meta.java_runtime is not None, "javaVersion lấy từ bản gốc"
    assert meta.asset_index is not None, "assetIndex lấy từ bản gốc"
    assert meta.inherits_from is None, "đã giải quyết xong thì không còn khoá này"


def test_the_jar_belongs_to_the_parent() -> None:
    """Bản Fabric không có jar riêng. Trỏ sai chỗ này là lỗi "không tìm thấy client.jar"."""
    meta = parse_version_meta(resolve_inheritance(FABRIC_ID, fixture_loader))
    assert meta.jar_owner_id == "1.21.4"


def test_loader_libraries_come_before_the_parent_ones() -> None:
    """Thứ tự này quyết định phiên bản nào thắng trên classpath.

    Fabric mang `asm` mới hơn vanilla; để vanilla lên trước là lỗi "duplicate classes".
    """
    child_libraries = as_list(load_fixture(FABRIC_ID).get("libraries"))
    child_names = {
        name
        for entry in child_libraries
        if (name := as_string(as_mapping(entry).get("name"))) is not None
    }
    meta = parse_version_meta(resolve_inheritance(FABRIC_ID, fixture_loader))
    leading = {str(library.coordinate) for library in meta.libraries[: len(child_libraries)]}
    assert leading == child_names


def test_parent_arguments_come_before_the_child_ones() -> None:
    """Ngược với thư viện: bản gốc dựng cả dòng lệnh, bản con chỉ THÊM vào."""
    parent_jvm = as_list(as_mapping(load_fixture("1.21.4").get("arguments")).get("jvm"))
    merged = resolve_inheritance(FABRIC_ID, fixture_loader)
    merged_jvm = as_list(as_mapping(merged.get("arguments")).get("jvm"))
    assert merged_jvm[: len(parent_jvm)] == parent_jvm
    assert len(merged_jvm) > len(parent_jvm)


def test_a_version_without_inheritance_is_returned_as_is() -> None:
    merged = resolve_inheritance("1.20.1", fixture_loader)
    assert merged["id"] == "1.20.1"


def test_a_cycle_fails_loudly_instead_of_hanging() -> None:
    """Đây là vòng lặp vô tận nếu không chặn: A kế thừa B, B kế thừa A."""
    documents: dict[str, JsonValue] = {
        "a": {"id": "a", "inheritsFrom": "b"},
        "b": {"id": "b", "inheritsFrom": "a"},
    }
    with pytest.raises(VersionError, match="vòng tròn"):
        resolve_inheritance("a", lambda version_id: documents[version_id])


def test_self_inheritance_is_a_cycle_too() -> None:
    documents: dict[str, JsonValue] = {"a": {"id": "a", "inheritsFrom": "a"}}
    with pytest.raises(VersionError, match="vòng tròn"):
        resolve_inheritance("a", lambda version_id: documents[version_id])


def test_a_chain_deeper_than_the_cap_is_refused() -> None:
    depth = MAX_INHERITANCE_DEPTH + 3
    documents: dict[str, JsonValue] = {
        f"v{index}": {"id": f"v{index}", "inheritsFrom": f"v{index + 1}"} for index in range(depth)
    }
    documents[f"v{depth}"] = {"id": f"v{depth}"}
    with pytest.raises(VersionError, match="sâu quá"):
        resolve_inheritance("v0", lambda version_id: documents[version_id])


def test_a_missing_parent_says_which_version_is_missing() -> None:
    with pytest.raises(VersionError, match="'khong-co'"):
        resolve_inheritance("khong-co", lambda _version_id: None)


def test_merge_does_not_mutate_its_inputs() -> None:
    """Trộn xong mà sửa đối số là lỗi rất khó truy khi cùng một cha có nhiều con."""
    child: dict[str, JsonValue] = {"id": "con", "libraries": [{"name": "a:b:1"}]}
    parent: dict[str, JsonValue] = {"id": "cha", "libraries": [{"name": "c:d:2"}]}
    merge_inherited(child, parent)
    assert child == {"id": "con", "libraries": [{"name": "a:b:1"}]}
    assert parent == {"id": "cha", "libraries": [{"name": "c:d:2"}]}


def test_child_scalar_keys_override_the_parent() -> None:
    merged = merge_inherited({"id": "con", "type": "release"}, {"id": "cha", "type": "snapshot"})
    assert (merged["id"], merged["type"]) == ("con", "release")
