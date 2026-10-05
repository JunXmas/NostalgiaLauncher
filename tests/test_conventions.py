"""Quy ước viết code — GLOSSARY.md §1 và §2 phải là luật kiểm được, không chỉ là văn bản."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from source_tree import (
    ALL_FILES,
    REPOSITORY_ROOT,
    SOURCE_FILES,
    banned_names_from_glossary,
    code_line_count,
    imported_symbols,
    module_name,
    parse,
)

MAX_CODE_LINES = 200

FORBIDDEN_PREFIXES = ("get_", "do_", "handle_", "process_", "manage_")

# Miễn trừ TƯỜNG MINH, mỗi cái một lý do. Không nới lỏng luật bằng mẫu chung: một mẫu như
# `do_[A-Z]+` sẽ mở cửa cho mọi `do_Something` tự đặt.
NAMES_REQUIRED_BY_STDLIB = frozenset(
    {
        "do_GET",  # http.server.BaseHTTPRequestHandler định tuyến theo đúng tên này
        "do_POST",  # cùng lý do: tên phương thức chính là tên HTTP method
        "handle_error",  # socketserver.BaseServer gọi đúng tên này khi xử lý request lỗi
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
        # `ui/app.py` cũng được: khi QML không nạp nổi, cửa sổ không mở ra, và stderr là
        # kênh duy nhất còn lại để nói cho người dùng biết vì sao. Chỉ ĐÚNG file điểm vào,
        # không phải cả gói ui/ — một `print` lạc trong phần vẽ vẫn là lỗi.
        if module_name(path) not in {"ui/app"} and not module_name(path).startswith("cli")
        for node in ast.walk(parse(path))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]
    assert not problems, "print() ngoài cli/:\n" + "\n".join(problems)


def test_naming_follows_the_glossary() -> None:
    """Áp cho cả `tests/` và `bench/`: một khái niệm phải mang một tên ở mọi nơi trong kho.

    Danh sách cấm đọc THẲNG từ GLOSSARY.md §2, không chép tay: chép tay thì tài liệu và test
    trôi khỏi nhau, và đã trôi thật — GLOSSARY cấm 70 tên trong khi test chỉ gác 32.
    """
    forbidden_names = banned_names_from_glossary()
    problems = []
    for path in ALL_FILES:
        allowed_here = forbidden_names - imported_symbols(path)
        for node in ast.walk(parse(path)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (
                    node.name.startswith(FORBIDDEN_PREFIXES)
                    and node.name not in NAMES_REQUIRED_BY_STDLIB
                ):
                    problems.append(f"{path.name}:{node.lineno}: hàm {node.name}()")
                problems.extend(
                    f"{path.name}:{node.lineno}: tham số {argument.arg}"
                    for argument in node.args.args + node.args.kwonlyargs
                    if argument.arg in allowed_here
                )
            elif isinstance(node, ast.Name) and node.id in allowed_here:
                problems.append(f"{path.name}:{node.lineno}: tên {node.id}")
    assert not problems, "trái GLOSSARY.md §2:\n" + "\n".join(problems)


def test_no_two_test_files_share_a_basename() -> None:
    """pytest không thu thập được hai file test trùng tên cơ sở khi không có `__init__.py`.

    Nó báo "import file mismatch" và **dừng toàn bộ lượt chạy**, nên một file mới đặt trùng
    tên sẽ làm CI đỏ theo cách chẳng liên quan gì tới nội dung file đó. Đã trả giá với
    `tests/account/test_store.py` và `tests/instance/test_store.py`.
    """
    seen: dict[str, Path] = {}
    clashes = []
    for path in sorted(REPOSITORY_ROOT.glob("tests/**/test_*.py")):
        earlier = seen.get(path.name)
        if earlier is not None:
            clashes.append(f"{earlier} và {path}")
        seen[path.name] = path
    assert not clashes, "hai file test trùng tên cơ sở:\n" + "\n".join(clashes)


def test_files_stay_short() -> None:
    """Áp cho cả kho, kể cả chính các file test — luật không chừa ai."""
    problems = [
        f"{path.name}: {count} dòng code"
        for path in ALL_FILES
        if (count := code_line_count(path)) > MAX_CODE_LINES
    ]
    assert not problems, f"quá {MAX_CODE_LINES} dòng code:\n" + "\n".join(problems)


def test_only_the_net_package_touches_http_and_tls() -> None:
    """`http.client` và `ssl` chỉ được xuất hiện trong `net/`.

    Đây là phiên bản kiểm được của luật 3 ở docs/PERFORMANCE.md. Bản đầu viết là "không
    module nào ở tầng lõi được import `http.client`" — nhưng chính `net/http.py` buộc phải
    import nó, nên luật đó không thể đúng theo mặt chữ. Luật thật: gói `net/` độc quyền giữ
    kiến thức về HTTP, và không gì trên đường nhanh của CLI được chạm vào `net/`.
    """
    network_modules = {"http", "http.client", "ssl"}
    problems: list[str] = []
    for path in SOURCE_FILES:
        name = module_name(path)
        if name.startswith("net"):
            continue
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.Import):
                problems.extend(
                    f"{name}:{node.lineno}: import {alias.name}"
                    for alias in node.names
                    if alias.name in network_modules
                )
            elif isinstance(node, ast.ImportFrom) and node.module in network_modules:
                problems.append(f"{name}:{node.lineno}: from {node.module} import ...")
    assert not problems, "chỉ net/ được biết về HTTP và TLS:\n" + "\n".join(problems)


def test_fast_path_does_not_load_heavy_modules() -> None:
    """`nostalgia --version` không được kéo theo module nặng.

    Ngân sách khởi động phụ thuộc hoàn toàn vào điều này, và thủ phạm đắt nhất là
    `http.client` chứ không phải thư viện ngoài nào — xem docs/PERFORMANCE.md §3.5.
    """
    code = (
        "import sys, io, contextlib\n"
        "from nostalgia.cli.main import main\n"
        "with contextlib.redirect_stdout(io.StringIO()):\n"
        "    try: main(['--version'])\n"
        "    except SystemExit: pass\n"
        f"sys.stderr.write(','.join(m for m in {HEAVY_MODULES!r} if m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stderr == "", f"module nặng bị nạp sẵn ở đường nhanh: {result.stderr}"
