"""Luật phụ thuộc giữa các tầng — sơ đồ ở GLOSSARY.md §5 phải đúng, không chỉ được viết ra."""

from __future__ import annotations

import ast
from collections import defaultdict

import pytest

from source_tree import SOURCE_FILES, imported_modules, layer_of, module_name, parse


def test_every_module_has_a_declared_layer() -> None:
    """Module không có tầng thì luật phụ thuộc không áp được lên nó."""
    orphans = [module_name(path) for path in SOURCE_FILES if layer_of(module_name(path)) is None]
    assert not orphans, f"chưa khai tầng trong LAYERS: {orphans}"


def test_layer_imports_only_go_down_or_sideways() -> None:
    """Tầng N import được tầng nhỏ hơn N và cùng tầng, không bao giờ ngược lên."""
    problems = []
    for path in SOURCE_FILES:
        name = module_name(path)
        own_layer = layer_of(name)
        assert own_layer is not None, f"{name} chưa khai tầng"
        for imported in imported_modules(path):
            other_layer = layer_of(imported)
            if other_layer is not None and other_layer > own_layer:
                problems.append(f"{name} (L{own_layer}) -> {imported} (L{other_layer})")
    assert not problems, "import ngược tầng:\n" + "\n".join(problems)


def test_imports_have_no_cycles() -> None:
    """Cùng tầng được phép import nhau, nhưng đồ thị phải phi chu trình.

    Bắt cả vòng độ dài 1 (module tự import chính nó) và chuỗi sâu — đã kiểm với 300 tầng,
    không tràn stack vì độ sâu bị chặn bởi số module.
    """
    graph: dict[str, set[str]] = defaultdict(set)
    for path in SOURCE_FILES:
        graph[module_name(path)] = set(imported_modules(path))

    cycles: list[str] = []
    visiting: list[str] = []
    done: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cycles.append(" -> ".join([*visiting[visiting.index(node) :], node]))
            return
        if node in done:
            return
        visiting.append(node)
        for target in sorted(graph.get(node, ())):
            visit(target)
        visiting.pop()
        done.add(node)

    for node in sorted(graph):
        visit(node)
    assert not cycles, "chu trình import:\n" + "\n".join(cycles)


def test_version_package_stays_pure() -> None:
    """`version/` không được chạm mạng hay đọc/ghi file — bất biến quý nhất của kiến trúc.

    Luật tầng KHÔNG bảo vệ được điều này: `version/` ở L2 vẫn được phép import `net/` ở L1.
    Vì thế phải có test riêng. (Bỏ qua khi gói chưa tồn tại; nó có từ bước 4.)
    """
    version_files = [p for p in SOURCE_FILES if module_name(p).startswith("version")]
    if not version_files:
        pytest.skip("chưa có gói version/ — sẽ có từ bước 4")

    banned_calls = {"open", "read_text", "write_text", "read_bytes", "write_bytes", "mkdir"}
    problems: list[str] = []
    for path in version_files:
        problems.extend(
            f"{module_name(path)} import {imported}"
            for imported in imported_modules(path)
            if imported.startswith("net")
        )
        for node in ast.walk(parse(path)):
            if not isinstance(node, ast.Call):
                continue
            target = node.func
            called = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
            if called in banned_calls:
                problems.append(f"{module_name(path)}:{node.lineno}: gọi {called}()")
    assert not problems, "version/ phải thuần:\n" + "\n".join(problems)
