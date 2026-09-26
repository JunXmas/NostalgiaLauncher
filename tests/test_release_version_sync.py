"""Phiên bản ghi ở hai chỗ (pyproject và `__version__`) phải khớp: bộ tự cập nhật so
`__version__` với tag release, còn tag lại được workflow kiểm với pyproject."""

from __future__ import annotations

import tomllib
from pathlib import Path

from nostalgia import __version__
from nostalgia.update.release import is_newer, parse_version


def test_pyproject_and_package_agree_on_the_version() -> None:
    pyproject = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == __version__
    assert parse_version(__version__) is not None, "phiên bản phải đọc được để so với release"
    assert is_newer(f"v{__version__}", __version__) is False


def test_the_lockfile_knows_the_current_version() -> None:
    """`uv.lock` ghi phiên bản của chính gói này. Quên `uv lock` sau khi bump thì CI đổ ở
    `uv sync --locked` — đã đổ đúng một lần ở tag v1.1.0, tức là sau khi tag đã đẩy đi và
    không rút lại được. Bắt ở đây rẻ hơn nhiều."""
    lock = tomllib.loads((Path(__file__).resolve().parents[1] / "uv.lock").read_bytes().decode())
    ours = [package for package in lock["package"] if package["name"] == "nostalgia"]
    assert ours, "uv.lock không có gói nostalgia"
    assert ours[0]["version"] == __version__, "chạy `uv lock` sau khi đổi phiên bản"
