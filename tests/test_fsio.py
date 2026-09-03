"""fsio: ghi nguyên tử, băm, và chặn đường dẫn thoát ra ngoài."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from mccore.errors import DataFileError, UnsafePathError
from mccore.fsio import (
    atomic_write_json,
    ensure_dir,
    read_json,
    safe_join,
    set_executable,
    sha1_of_file,
)

# sha1 của chuỗi rỗng và của b"abc" — giá trị chuẩn, tra được ở bất cứ đâu.
SHA1_EMPTY = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
SHA1_ABC = "a9993e364706816aba3e25717850c26c9cd0d89d"

ESCAPING_PATHS = [
    "../thoat.txt",
    "a/../../thoat.txt",
    "/tuyet/doi.txt",
    "a/b/../../../thoat.txt",
    r"C:\Windows\system32\evil.dll",
    r"\\may-chu\o-dia\evil.dll",
    r"\tuyet-doi-kieu-windows",
]


def test_ensure_dir_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c"
    assert ensure_dir(target) == target
    assert ensure_dir(target).is_dir()


@pytest.mark.parametrize("relative", ESCAPING_PATHS)
def test_safe_join_blocks_escape(tmp_path: Path, relative: str) -> None:
    """Zip-slip: một entry tên `../../.bashrc` phải thành lỗi, không thành file bị ghi đè."""
    with pytest.raises(UnsafePathError):
        safe_join(tmp_path, relative)


@pytest.mark.parametrize("relative", ["a.txt", "a/b.txt", "./a/b.txt", "a/./b/../c.txt"])
def test_safe_join_allows_paths_inside(tmp_path: Path, relative: str) -> None:
    result = safe_join(tmp_path, relative)
    assert result.is_relative_to(tmp_path.resolve())


def test_safe_join_blocks_symlink_pointing_outside(tmp_path: Path) -> None:
    outside = tmp_path / "ngoai"
    outside.mkdir()
    base = tmp_path / "trong"
    base.mkdir()
    (base / "loi-tat").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafePathError):
        safe_join(base, "loi-tat/evil.txt")


def test_sha1_of_file(tmp_path: Path) -> None:
    empty = tmp_path / "rong"
    empty.write_bytes(b"")
    assert sha1_of_file(empty) == SHA1_EMPTY
    abc = tmp_path / "abc"
    abc.write_bytes(b"abc")
    assert sha1_of_file(abc) == SHA1_ABC


def test_sha1_reads_files_larger_than_one_chunk(tmp_path: Path) -> None:
    import hashlib

    payload = os.urandom(3 * (1 << 20) + 7)
    big = tmp_path / "to"
    big.write_bytes(payload)
    assert sha1_of_file(big) == hashlib.sha1(payload).hexdigest()


def test_read_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "a.json"
    atomic_write_json(path, {"ten": "jun", "so": [1, 2, 3]})
    assert read_json(path) == {"ten": "jun", "so": [1, 2, 3]}


def test_read_json_reports_the_offending_path(tmp_path: Path) -> None:
    missing = tmp_path / "khong-co.json"
    with pytest.raises(DataFileError, match=r"khong-co\.json"):
        read_json(missing)

    broken = tmp_path / "hong.json"
    broken.write_text("{ khong phai json", encoding="utf-8")
    with pytest.raises(DataFileError, match=r"hong\.json"):
        read_json(broken)


def test_atomic_write_leaves_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "a.json"
    atomic_write_json(path, {"x": 1})
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]


def test_atomic_write_replaces_previous_content(tmp_path: Path) -> None:
    path = tmp_path / "a.json"
    atomic_write_json(path, {"cu": True})
    atomic_write_json(path, {"moi": True})
    assert read_json(path) == {"moi": True}


def test_atomic_write_keeps_old_file_when_serialising_fails(tmp_path: Path) -> None:
    """Nếu dữ liệu không tuần tự hoá được, file cũ phải còn nguyên và không sót file tạm."""
    path = tmp_path / "a.json"
    atomic_write_json(path, {"cu": True})
    with pytest.raises(TypeError):
        atomic_write_json(path, {"khong-tuan-tu-hoa-duoc": object()})  # type: ignore[dict-item]
    assert read_json(path) == {"cu": True}
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]


def test_private_files_are_not_world_readable(tmp_path: Path) -> None:
    """File chứa vé đăng nhập không được để người dùng khác trên máy đọc."""
    path = tmp_path / "accounts.json"
    atomic_write_json(path, {"token": "bi-mat"}, private=True)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_normal_files_are_readable(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    atomic_write_json(path, {"ram": 2048})
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_atomic_write_creates_missing_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "c.json"
    atomic_write_json(path, {"x": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"x": 1}


def test_set_executable_keeps_existing_permissions(tmp_path: Path) -> None:
    path = tmp_path / "java"
    path.write_bytes(b"")
    path.chmod(0o640)
    set_executable(path)
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode & stat.S_IXUSR
    assert mode & stat.S_IRUSR and mode & stat.S_IWUSR
