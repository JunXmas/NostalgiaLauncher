"""Quy ước viết code — GLOSSARY.md §1 và §2 phải là luật kiểm được, không chỉ là văn bản."""

from __future__ import annotations

import ast
import subprocess
import sys

from source_tree import ALL_FILES, SOURCE_FILES, code_line_count, module_name, parse

MAX_CODE_LINES = 200

FORBIDDEN_PREFIXES = ("get_", "do_", "handle_", "process_", "manage_")

# Những tên đã gây ra lỗi thật ở launcher tiền nhiệm, hoặc bị GLOSSARY §2 cấm thẳng.
FORBIDDEN_NAMES = frozenset(
    {
        "store_root",
        "game_root",
        "mc_dir",
        "minecraft_dir",
        "run_dir",
        "base_dir",
        "mc",
        "mcver",
        "vid",
        "ver",
        "mc_version",
        "base_version",
        "lib",
        "libs",
        "coord",
        "gav",
        "cp",
        "cp_list",
        "cp_str",
        "idx",
        "index_json",
        "obj",
        "acc",
        "username",
        "nick",
        "token",
        "tk",
        "java_path",
        "jvm",
        "jre",
        "proc",
        "job",
    }
)

# Module nặng: nạp chúng ở đường nhanh là vỡ ngân sách khởi động (docs/PERFORMANCE.md §3.5).
HEAVY_MODULES = ("http.client", "ssl", "zipfile", "concurrent.futures", "subprocess", "logging")


def test_no_module_level_path_constants() -> None:
    """Chặn đúng nguyên nhân gốc của lỗi mất dữ liệu ở launcher tiền nhiệm.

    Kho cũ khai `CONFIG_DIR, CACHE_DIR, DEFAULT_GAME_DIR = _dirs()` ở mức module, tính từ
    `Path.home()` ngay lúc import — chỉ một dòng import sớm trong test là ghi đè config thật.

    Lưới lúc chạy trong `conftest.py` **không bắt được** trường hợp này: lệnh import chạy lúc
    pytest thu thập test, trước khi fixture kịp vá `Path.home`. Chỉ test đọc mã nguồn mới bắt.
    """
    dangerous = ("Path.home", "expanduser", "os.environ", "getenv")
    problems = []
    for path in SOURCE_FILES:
        for node in parse(path).body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                expression = ast.unparse(node.value)
                if any(marker in expression for marker in dangerous):
                    problems.append(f"{module_name(path)}:{node.lineno}: {expression}")
    assert not problems, "đường dẫn phải đến từ DataPaths được tiêm vào:\n" + "\n".join(problems)


def test_core_never_prints() -> None:
    """Lõi báo tiến độ qua `on_progress`, báo diễn biến qua `logging`. Chỉ `cli/` được in."""
    problems = [
        f"{module_name(path)}:{node.lineno}"
        for path in SOURCE_FILES
        if not module_name(path).startswith("cli")
        for node in ast.walk(parse(path))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]
    assert not problems, "print() ngoài cli/:\n" + "\n".join(problems)


def test_naming_follows_the_glossary() -> None:
    """Áp cho cả `tests/` và `bench/`: một khái niệm phải mang một tên ở mọi nơi trong kho."""
    problems = []
    for path in ALL_FILES:
        for node in ast.walk(parse(path)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith(FORBIDDEN_PREFIXES):
                    problems.append(f"{path.name}:{node.lineno}: hàm {node.name}()")
                problems.extend(
                    f"{path.name}:{node.lineno}: tham số {argument.arg}"
                    for argument in node.args.args + node.args.kwonlyargs
                    if argument.arg in FORBIDDEN_NAMES
                )
            elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                problems.append(f"{path.name}:{node.lineno}: tên {node.id}")
    assert not problems, "trái GLOSSARY.md §2:\n" + "\n".join(problems)


def test_files_stay_short() -> None:
    """Áp cho cả kho, kể cả chính các file test — luật không chừa ai."""
    problems = [
        f"{path.name}: {count} dòng code"
        for path in ALL_FILES
        if (count := code_line_count(path)) > MAX_CODE_LINES
    ]
    assert not problems, f"quá {MAX_CODE_LINES} dòng code:\n" + "\n".join(problems)


def test_fast_path_does_not_load_heavy_modules() -> None:
    """`mccore --version` không được kéo theo module nặng.

    Ngân sách khởi động phụ thuộc hoàn toàn vào điều này, và thủ phạm đắt nhất là
    `http.client` chứ không phải thư viện ngoài nào — xem docs/PERFORMANCE.md §3.5.
    """
    code = (
        "import sys, io, contextlib\n"
        "from mccore.cli.main import main\n"
        "with contextlib.redirect_stdout(io.StringIO()):\n"
        "    try: main(['--version'])\n"
        "    except SystemExit: pass\n"
        f"sys.stderr.write(','.join(m for m in {HEAVY_MODULES!r} if m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stderr == "", f"module nặng bị nạp sẵn ở đường nhanh: {result.stderr}"
