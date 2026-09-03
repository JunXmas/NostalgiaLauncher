"""Test khung của bước 1: gói import sạch, CLI thật chạy được, và lưới cách ly có răng."""

from __future__ import annotations

import importlib
import os
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest

import mccore
from mccore.cli.main import build_parser, main

PACKAGE_ROOT = Path(mccore.__path__[0])


def _module_names_on_disk() -> set[str]:
    """Mọi module .py thật sự nằm trong gói, kể cả trong thư mục thiếu __init__.py."""
    names = set()
    for path in PACKAGE_ROOT.rglob("*.py"):
        parts = path.relative_to(PACKAGE_ROOT).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.add(".".join(("mccore", *parts)))
    names.discard("mccore")
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
    walked = {info.name for info in pkgutil.walk_packages(mccore.__path__, prefix="mccore.")}
    assert walked == _module_names_on_disk()


def test_version_is_declared() -> None:
    assert mccore.__version__


def test_cli_without_arguments_prints_help_and_returns_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: mccore")
    assert captured.err == ""


def test_cli_version_flag_prints_version_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0
    assert mccore.__version__ in capsys.readouterr().out


def test_cli_rejects_unknown_argument() -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--khong-ton-tai"])
    assert exit_info.value.code != 0


def test_installed_console_script_runs() -> None:
    """Chạy đúng đường người dùng đi: entry point trong pyproject, qua một tiến trình thật.

    Các test trên chỉ gọi hàm; test này gác luôn [project.scripts] và cấu hình đóng gói.
    """
    code = "from mccore.cli.main import main; raise SystemExit(main(['--version']))"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert mccore.__version__ in result.stdout


def test_home_access_is_forbidden() -> None:
    """Lưới an toàn phải BẮT lỗi chứ không che lỗi: chạm home là rớt ngay."""
    with pytest.raises(AssertionError, match="DataPaths"):
        Path.home()
    with pytest.raises(AssertionError, match="DataPaths"):
        os.path.expanduser("~")  # noqa: PTH111 - đang cố tình kiểm chính lối đi này


@pytest.mark.allow_home
def test_home_is_redirected_when_allowed(tmp_path: Path) -> None:
    """Với test được phép chạm home, home vẫn phải nằm trong thư mục tạm."""
    assert Path.home().is_relative_to(tmp_path)
