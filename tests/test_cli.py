"""Test khung của bước 1: gói import sạch, CLI thật chạy được, và lưới cách ly có răng."""

from __future__ import annotations

import importlib
import os
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest

import nostalgia
from nostalgia.cli.main import build_parser, main

PACKAGE_ROOT = Path(nostalgia.__path__[0])


def _module_names_on_disk() -> set[str]:
    """Mọi module .py thật sự nằm trong gói, kể cả trong thư mục thiếu __init__.py."""
    names = set()
    for path in PACKAGE_ROOT.rglob("*.py"):
        parts = path.relative_to(PACKAGE_ROOT).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.add(".".join(("nostalgia", *parts)))
    names.discard("nostalgia")
    return names


def test_every_module_imports() -> None:
    """Mọi module trong gói phải import được — bắt lỗi cú pháp và import vòng sớm."""
    for name in sorted(_module_names_on_disk()):
        importlib.import_module(name)


def test_no_module_is_invisible_to_pkgutil() -> None:
    """pkgutil bỏ qua thư mục thiếu __init__.py, nên module hỏng trong đó sẽ vô hình.

    So tập module mà pkgutil thấy với tập file .py thật trên đĩa; lệch nghĩa là có gói con
    quên __init__.py — nó vẫn được đóng gói và vẫn gãy lúc chạy, chỉ là CI không biết.
    """
    walked = {info.name for info in pkgutil.walk_packages(nostalgia.__path__, prefix="nostalgia.")}
    assert walked == _module_names_on_disk()


def test_version_is_declared() -> None:
    assert nostalgia.__version__


def test_cli_without_arguments_prints_help_and_returns_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: nostalgia")
    assert captured.err == ""


def test_cli_version_flag_prints_version_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0
    assert nostalgia.__version__ in capsys.readouterr().out


def test_cli_rejects_unknown_argument() -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--khong-ton-tai"])
    assert exit_info.value.code != 0


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Chạy CLI qua đúng đường người dùng đi: main() trong một tiến trình thật."""
    code = f"from nostalgia.cli.main import main; raise SystemExit(main({list(args)!r}))"
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)


def test_main_propagates_argparse_exit_code() -> None:
    """main() KHÔNG được nuốt SystemExit của argparse.

    Test `test_cli_rejects_unknown_argument` ở trên gọi thẳng parse_args, tức đi vòng qua
    main(). Nếu ai đó bọc main bằng `try/except SystemExit: return 0` thì đối số sai sẽ trả
    mã 0 mà bộ test vẫn xanh — đã kiểm bằng đột biến và đúng là lọt. Test này bịt lỗ đó.
    """
    result = _run_cli("--khong-ton-tai")
    assert result.returncode != 0
    assert "khong-ton-tai" in result.stderr


def test_installed_console_script_runs() -> None:
    """Chạy đúng đường người dùng đi: entry point trong pyproject, qua một tiến trình thật."""
    result = _run_cli("--version")
    assert result.returncode == 0, result.stderr
    assert nostalgia.__version__ in result.stdout


def test_cli_stays_light() -> None:
    """Lệnh không chạm mạng không được kéo theo module nặng.

    Ngân sách khởi động ở docs/PERFORMANCE.md phụ thuộc hoàn toàn vào điều này, và thủ phạm
    đắt nhất là http.client chứ không phải thư viện ngoài nào.
    """
    heavy = ("http.client", "ssl", "zipfile", "concurrent.futures", "subprocess", "logging")
    code = (
        "import sys, io, contextlib\n"
        "from nostalgia.cli.main import main\n"
        "with contextlib.redirect_stdout(io.StringIO()):\n"
        "    try: main(['--version'])\n"
        "    except SystemExit: pass\n"
        f"sys.stderr.write(','.join(m for m in {heavy!r} if m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stderr == "", f"module nặng bị nạp sẵn: {result.stderr}"


def test_home_access_is_forbidden() -> None:
    """Lưới an toàn phải BẮT lỗi chứ không che lỗi: chạm home là rớt ngay."""
    with pytest.raises(AssertionError, match="DataPaths"):
        Path.home()
    with pytest.raises(AssertionError, match="DataPaths"):
        os.path.expanduser("~")  # noqa: PTH111 - đang cố tình kiểm chính lối đi này


@pytest.mark.allow_home
def test_home_is_redirected_when_allowed(isolated_home: Path) -> None:
    """Với test được phép chạm home, home vẫn phải là thư mục tạm mà fixture dựng."""
    assert Path.home() == isolated_home
