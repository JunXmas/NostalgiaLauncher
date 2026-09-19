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


def test_release_workflow_only_triggers_on_plain_version_tags() -> None:
    """`v1.0.10-hotfix` từng khởi chạy workflow rồi chết ở bước so tag với `__version__`.
    Bộ lọc tag phải loại hậu tố ngay từ đầu."""
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/release.yml").read_text()
    assert 'tags: ["v[0-9]+.[0-9]+.[0-9]+"]' in workflow, "bộ lọc tag phải chặn hậu tố"
    assert 'tags: ["v*"]' not in workflow


def test_preflight_script_checks_every_gate_the_workflow_does() -> None:
    """Preflight ở máy phải chạy đúng các cổng của job `check` — thiếu một cổng là lại
    phát hiện lỗi sau khi tag đã đẩy."""
    repo_dir = Path(__file__).resolve().parents[1]
    script = (repo_dir / "scripts/preflight-release.sh").read_text()
    for gate in ("ruff check", "ruff format --check", "mypy", 'pytest -m "not network"'):
        assert gate in script, f"preflight thiếu cổng: {gate}"
