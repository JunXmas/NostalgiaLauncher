"""Đọc cây mã nguồn bằng `ast` — phần dùng chung của các test soi kiến trúc và quy ước.

Tách riêng vì hai bộ test (`test_architecture.py` và `test_conventions.py`) cùng cần một
cách nhìn về cây nguồn, và vì gộp tất cả vào một file test làm nó vượt chính luật 200 dòng
mà nó đi kiểm.
"""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path

import mccore

PACKAGE_ROOT = Path(mccore.__path__[0])
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]

SOURCE_FILES = sorted(PACKAGE_ROOT.rglob("*.py"))

# Luật ĐẶT TÊN và ĐỘ DÀI áp cho cả kho: một khái niệm phải mang một tên ở mọi nơi. Các luật
# khác (không `print`, không hằng `Path` mức module) chỉ áp lên lõi, vì `bench/` cần cả hai.
ALL_FILES = SOURCE_FILES + sorted(
    path for directory in ("tests", "bench") for path in (REPOSITORY_ROOT / directory).rglob("*.py")
)

# Tầng của từng module, theo sơ đồ ở GLOSSARY.md §5. Khoá là đường dẫn trong gói.
LAYERS: dict[str, int] = {
    "": 0,  # chính `mccore/__init__.py`: không được import gì của gói
    "errors": 0,  # từ vựng lỗi, mọi tầng đều dùng nên cố tình để ở gốc
    "storage": 0,  # đĩa: paths (cái gì ở đâu) + files (đọc/ghi an toàn)
    "system": 0,  # nhận diện máy
    "operations": 0,  # báo tiến độ, yêu cầu dừng
    "model": 0,  # dataclass dùng chung (thêm ở bước 3)
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


@cache
def parse(path: Path) -> ast.Module:
    """Cây cú pháp của một file, nhớ lại giữa các test.

    Các test gác cùng soi một tập file, nên không nhớ lại thì mỗi file bị phân tích gần năm
    lần: 26 ms hôm nay, khoảng 115 ms khi lõi lên 40 file. File không đổi trong lúc chạy
    test nên nhớ lại là an toàn.
    """
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def module_name(path: Path) -> str:
    """Đường dẫn của module trong gói, ví dụ `cli/main`. Gói gốc là chuỗi rỗng."""
    parts = path.relative_to(PACKAGE_ROOT).with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return "/".join(parts)


def as_package_path(dotted: str) -> str:
    """Đổi `mccore.cli.main` thành `cli/main`, và `mccore` thành chuỗi rỗng.

    Chuỗi rỗng là tên của chính `mccore/__init__.py` trong `LAYERS`. Không quy về cùng một
    tên thì cạnh `from mccore import __version__` trỏ tới một node không tồn tại, và luật
    tầng lặng lẽ bỏ qua nó.
    """
    return dotted.removeprefix("mccore").removeprefix(".").replace(".", "/")


def layer_of(name: str) -> int | None:
    """Tầng của một module; khớp tiền tố dài nhất để `java/component` thắng `java`."""
    candidates = [prefix for prefix in LAYERS if name == prefix or name.startswith(prefix + "/")]
    if not candidates:
        return None
    return LAYERS[max(candidates, key=len)]


def imported_modules(path: Path) -> list[str]:
    """Các module *của mccore* mà file này import, dưới dạng đường dẫn trong gói."""
    found = []
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("mccore"):
            found.append(as_package_path(node.module))
        elif isinstance(node, ast.Import):
            found.extend(
                as_package_path(alias.name)
                for alias in node.names
                if alias.name == "mccore" or alias.name.startswith("mccore.")
            )
    return found


def code_line_count(path: Path) -> int:
    """Số dòng code, không tính docstring, chú thích và dòng trống.

    Đếm bằng Python chứ không bằng `awk length`: `awk` đếm byte nên dòng tiếng Việt có dấu
    bị báo dài gấp rưỡi. Đã trả giá một lần vì chuyện này.
    """
    text = path.read_text(encoding="utf-8")
    skip: set[int] = set()
    for node in ast.walk(parse(path)):
        if not isinstance(node, ast.Expr):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        skip.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return sum(
        1
        for number, line in enumerate(text.splitlines(), 1)
        if line.strip() and not line.strip().startswith("#") and number not in skip
    )
