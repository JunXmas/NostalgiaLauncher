"""Test khung của bước 1: gói import sạch, CLI chạy, và test bị cách ly khỏi HOME thật."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

import mccore
from mccore.cli.main import build_parser, main


def test_every_module_imports() -> None:
    """Mọi module trong gói phải import được — bắt lỗi cú pháp và import vòng sớm."""
    imported = []
    for module_info in pkgutil.walk_packages(mccore.__path__, prefix="mccore."):
        importlib.import_module(module_info.name)
        imported.append(module_info.name)
    assert "mccore.cli.main" in imported


def test_version_is_declared() -> None:
    assert mccore.__version__


def test_cli_without_arguments_prints_help_and_returns_zero(capsys) -> None:
    assert main([]) == 0
    assert "mccore" in capsys.readouterr().out


def test_cli_version_flag_prints_version_and_exits_zero(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0
    assert mccore.__version__ in capsys.readouterr().out


def test_cli_rejects_unknown_argument() -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--khong-ton-tai"])
    assert exit_info.value.code != 0


def test_home_is_isolated(tmp_path) -> None:
    """Nếu test này rớt, mọi test khác đều có nguy cơ ghi vào dữ liệu thật của người dùng."""
    assert Path.home().is_relative_to(tmp_path)
