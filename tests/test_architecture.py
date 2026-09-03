"""Bảy test gác biến luật trong GLOSSARY.md thành thứ CI kiểm được.

Luật viết trong tài liệu mà không ai kiểm thì chỉ là mong muốn. Bảy test dưới đây soi mã
nguồn bằng `ast`, và **chỉ áp lên `src/mccore/`** — `bench/` được miễn vì nó phải in ra màn
hình và phải có đường dẫn mặc định, `tests/` được miễn vì nó chính là nơi kiểm.

Mỗi test tương ứng một dòng trong bảng ở GLOSSARY.md §4.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest

import mccore

PACKAGE_ROOT = Path(mccore.__path__[0])
SOURCE_FILES = sorted(PACKAGE_ROOT.rglob("*.py"))

MAX_CODE_LINES = 200

# Tầng của từng module, theo sơ đồ ở GLOSSARY.md §5. Khoá là tiền tố đường dẫn trong gói.
LAYERS: dict[str, int] = {
    "": 0,  # chính `mccore/__init__.py`: không được import gì của gói
    "errors": 0,
    "platform_info": 0,
    "paths": 0,
    "fsio": 0,
    "progress": 0,
    "cancel": 0,
    "model": 0,
    "net": 1,
    "version": 2,
    "java/component": 2,
    "repo": 3,
    "install": 3,
    "java": 3,
    "account": 4,
    "launch": 4,
    "doctor": 4,
    "api": 5,
    "cli": 6,
    "config": 6,
}

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


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def module_name(path: Path) -> str:
    parts = path.relative_to(PACKAGE_ROOT).with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return "/".join(parts)


def layer_of(name: str) -> int | None:
    """Tầng của một module; khớp tiền tố dài nhất để `java/component` thắng `java`."""
    candidates = [prefix for prefix in LAYERS if name == prefix or name.startswith(prefix + "/")]
    if not candidates:
        return None
    return LAYERS[max(candidates, key=len)]


def docstring_lines(tree: ast.Module) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def test_every_module_has_a_declared_layer() -> None:
    """Module không có tầng thì luật phụ thuộc không áp được lên nó."""
    orphans = [module_name(path) for path in SOURCE_FILES if layer_of(module_name(path)) is None]
    assert not orphans, f"chưa khai tầng trong LAYERS: {orphans}"


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


def test_layer_imports_only_go_down_or_sideways() -> None:
    problems = []
    for path in SOURCE_FILES:
        name = module_name(path)
        own_layer = layer_of(name)
        assert own_layer is not None
        for imported in imported_modules(parse(path)):
            other_layer = layer_of(imported)
            if other_layer is not None and other_layer > own_layer:
                problems.append(f"{name} (L{own_layer}) -> {imported} (L{other_layer})")
    assert not problems, "import ngược tầng:\n" + "\n".join(problems)


def test_imports_have_no_cycles() -> None:
    """Cùng tầng được phép import nhau, nhưng đồ thị phải phi chu trình."""
    graph = defaultdict(set)
    for path in SOURCE_FILES:
        graph[module_name(path)] = set(imported_modules(parse(path)))

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


def imported_modules(tree: ast.Module) -> list[str]:
    """Các module *của mccore* mà file này import, dưới dạng đường dẫn trong gói."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("mccore"):
            found.append(node.module.removeprefix("mccore.").replace(".", "/"))
        elif isinstance(node, ast.Import):
            found.extend(
                alias.name.removeprefix("mccore.").replace(".", "/")
                for alias in node.names
                if alias.name.startswith("mccore.")
            )
    return found


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


def test_version_package_is_pure() -> None:
    """`version/` không được chạm mạng hay đọc/ghi file — bất biến quý nhất của kiến trúc.

    Luật tầng KHÔNG bảo vệ được điều này: `version/` ở L2 vẫn được phép import `net/` ở L1.
    Vì thế phải có test riêng.
    """
    version_files = [p for p in SOURCE_FILES if module_name(p).startswith("version")]
    if not version_files:
        pytest.skip("chưa có gói version/ — sẽ có từ bước 4")

    banned_calls = {"open", "read_text", "write_text", "read_bytes", "write_bytes", "mkdir"}
    problems = []
    for path in version_files:
        for imported in imported_modules(parse(path)):
            if imported.startswith("net"):
                problems.append(f"{module_name(path)} import {imported}")
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.Call):
                target = node.func
                called = (
                    target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
                )
                if called in banned_calls:
                    problems.append(f"{module_name(path)}:{node.lineno}: gọi {called}()")
    assert not problems, "version/ phải thuần:\n" + "\n".join(problems)


def test_naming_follows_the_glossary() -> None:
    problems = []
    for path in SOURCE_FILES:
        name = module_name(path)
        for node in ast.walk(parse(path)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith(FORBIDDEN_PREFIXES):
                    problems.append(f"{name}:{node.lineno}: hàm {node.name}()")
                for argument in node.args.args + node.args.kwonlyargs:
                    if argument.arg in FORBIDDEN_NAMES:
                        problems.append(f"{name}:{node.lineno}: tham số {argument.arg}")
            elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                problems.append(f"{name}:{node.lineno}: tên {node.id}")
    assert not problems, "trái GLOSSARY.md §2:\n" + "\n".join(problems)


def test_files_stay_short() -> None:
    """Đếm dòng *code*, không tính docstring, chú thích và dòng trống.

    Đếm bằng Python chứ không bằng `awk length`: `awk` đếm byte nên dòng tiếng Việt có dấu
    bị báo dài gấp rưỡi. Đã trả giá một lần vì chuyện này.
    """
    problems = []
    for path in SOURCE_FILES:
        text = path.read_text(encoding="utf-8")
        skip = docstring_lines(ast.parse(text))
        code_lines = sum(
            1
            for number, line in enumerate(text.splitlines(), 1)
            if line.strip() and not line.strip().startswith("#") and number not in skip
        )
        if code_lines > MAX_CODE_LINES:
            problems.append(f"{module_name(path)}: {code_lines} dòng code")
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
