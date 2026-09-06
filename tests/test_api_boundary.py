"""Ranh giới lõi ↔ giao diện, biến thành thứ CI kiểm được.

Kho tiền nhiệm không có ranh giới này, và đo được hậu quả: phần giao diện của nó import
thẳng vào sáu module lõi. Ba test dưới đây làm cho chuyện đó không lặp lại được.
"""

from __future__ import annotations

import ast

import pytest

from source_tree import SOURCE_FILES, imported_modules, module_name, parse

# Giao diện chỉ được đi qua đúng những cửa này. Ý định của luật là chặn giao diện thò tay
# vào RUỘT của lõi — nên module của chính nó và số phiên bản của gói thì đương nhiên được.
ALLOWED_FOR_USER_INTERFACE = (
    "nostalgia.ui",
    "nostalgia.api",
    "nostalgia.errors",
    "nostalgia.operations.progress",
    "nostalgia.operations.cancellation",
    "nostalgia.model",
    "nostalgia.account.model",
    "nostalgia.instance.model",
    "nostalgia.content.model",
    "nostalgia.modloader.model",
    "nostalgia.multiplayer.model",
    "nostalgia.settings.store",
)

# Kiểu KHÔNG được xuất hiện trong chữ ký công khai của façade: chúng buộc người gọi phải biết
# về chi tiết bên trong, và `dict` thô thì không có kiểu nào bảo vệ.
LEAKY_RETURN_TYPES = ("dict", "Popen", "HTTPResponse", "HTTPSConnection", "ZipFile", "Response")


def facade_modules() -> list[ast.Module]:
    """`api.py` và toàn bộ thân của nó ở `facade/` — cùng một cửa, chỉ tách file."""
    modules = [
        parse(path)
        for path in SOURCE_FILES
        if module_name(path) == "api" or module_name(path).startswith("facade/")
    ]
    assert modules, "không tìm thấy nostalgia/api.py"
    return modules


def public_functions() -> list[ast.FunctionDef]:
    functions = []
    for module in facade_modules():
        for node in ast.walk(module):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                functions.append(node)
    return functions


def test_the_facade_exists_and_exposes_something() -> None:
    assert public_functions(), "façade rỗng thì giao diện không có gì để gọi"


def test_no_public_entry_point_returns_a_raw_dictionary() -> None:
    """Trả `dict` là đẩy cho giao diện tự đoán khoá nào có, và không kiểu nào bảo vệ."""
    problems = [
        f"{function.name}() -> {ast.unparse(function.returns)}"
        for function in public_functions()
        if function.returns is not None
        and any(leak in ast.unparse(function.returns) for leak in LEAKY_RETURN_TYPES)
    ]
    assert not problems, "façade rò kiểu nội bộ:\n" + "\n".join(problems)


def test_every_public_entry_point_declares_its_types() -> None:
    """Façade là hợp đồng; hợp đồng không có kiểu thì không phải hợp đồng."""
    problems = [function.name for function in public_functions() if function.returns is None]
    assert not problems, f"thiếu kiểu trả về: {problems}"


def test_a_future_user_interface_may_only_import_the_facade() -> None:
    """Chưa có `ui/` thì luật này chưa cắn, nhưng nó đã nằm sẵn ở đây chờ.

    Viết trước có chủ ý: thêm luật sau khi giao diện đã bám vào lõi thì không ai gỡ nổi nữa.
    """
    ui_files = [path for path in SOURCE_FILES if module_name(path).startswith("ui")]
    if not ui_files:
        pytest.skip("chưa có gói ui/ — luật này sẽ cắn ngay khi có")

    problems = []
    for path in ui_files:
        for imported in imported_modules(path):
            dotted = "nostalgia." + imported.replace("/", ".") if imported else "nostalgia"
            if dotted != "nostalgia" and not dotted.startswith(ALLOWED_FOR_USER_INTERFACE):
                problems.append(f"{module_name(path)} import {dotted}")
    assert not problems, "giao diện chỉ được import façade và mô hình:\n" + "\n".join(problems)
