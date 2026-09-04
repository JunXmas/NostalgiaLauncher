"""storage.files: ghi nguyên tử, băm, và chặn đường dẫn thoát ra ngoài."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from nostalgia.errors import DataFileError, UnsafePathError
from nostalgia.storage.files import (
    atomic_write_json,
    ensure_dir,
    read_json,
    resolve_child,
    resolve_within,
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
    "..",
    "a/..",
    "",
    ".",
    "./",
    r"C:\Windows\system32\evil.dll",
    r"\\may-chu\o-dia\evil.dll",
    r"\tuyet-doi-kieu-windows",
    r"a\..\..\thoat.txt",
]


def test_ensure_dir_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c"
    assert ensure_dir(target) == target
    assert ensure_dir(target).is_dir()


@pytest.mark.parametrize("relative", ESCAPING_PATHS)
def test_resolve_within_blocks_escape(tmp_path: Path, relative: str) -> None:
    """Zip-slip: một entry tên `../../.bashrc` phải thành lỗi, không thành file bị ghi đè."""
    with pytest.raises(UnsafePathError):
        resolve_within(tmp_path, relative)


@pytest.mark.parametrize("relative", ["a.txt", "a/b.txt", "./a/b.txt", "a//b.txt", "a/./b.txt"])
def test_resolve_within_allows_paths_inside(tmp_path: Path, relative: str) -> None:
    result = resolve_within(tmp_path, relative)
    assert result.is_relative_to(tmp_path.resolve())


def test_resolve_within_does_not_touch_the_filesystem(tmp_path: Path) -> None:
    """Hàm thuần chuỗi: `base` không cần tồn tại, và nó không gọi syscall nào.

    Đây là điều kiện để gọi được hàng nghìn lần trong vòng giải nén — bản dùng
    `Path.resolve()` tốn 177 µs mỗi lần, tức 618 ms cho một modpack 3.500 file.
    """
    chua_tao = tmp_path / "chua-tao"
    assert resolve_within(chua_tao, "a/b.txt") == chua_tao / "a" / "b.txt"


def test_resolve_within_rejects_dotdot_even_when_it_normalises_inside(tmp_path: Path) -> None:
    """`a/../b.txt` chuẩn hoá vào trong, nhưng vẫn bị từ chối — cố ý chặt hơn.

    Không entry archive lành mạnh nào cần `..` ở giữa đường dẫn. Chặn thẳng thì không phải
    tin vào việc chuẩn hoá đúng, và không mở đường cho các biến thể mã hoá lạ.
    """
    with pytest.raises(UnsafePathError, match=r"\.\."):
        resolve_within(tmp_path, "a/../b.txt")


def test_resolve_within_relies_on_caller_not_creating_symlinks(tmp_path: Path) -> None:
    """Ghi lại rõ giới hạn đã biết, để không ai tưởng hàm bảo vệ nhiều hơn thực tế.

    Vì thuần chuỗi, hàm KHÔNG phát hiện symlink đã có sẵn bên trong `base`. Bất biến mà
    người gọi phải giữ: không bao giờ tạo symlink từ nội dung archive. Khi mọi thư mục
    trong `base` đều do chính ta tạo, không có symlink nào tồn tại để đi qua.
    """
    base = tmp_path / "trong"
    base.mkdir()
    (base / "loi-tat").symlink_to(tmp_path / "ngoai", target_is_directory=True)
    # Không ném lỗi — theo đúng thiết kế. Phòng tuyến thật nằm ở bước giải nén.
    assert resolve_within(base, "loi-tat/x.txt") == base / "loi-tat" / "x.txt"


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


ESCAPING_NAMES = [
    "",
    ".",
    "..",
    "a/b",
    "a\\b",
    "/tuyet-doi",
    "..\\thoat",
    "C:x",
]


@pytest.mark.parametrize("name", ESCAPING_NAMES)
def test_resolve_child_rejects_anything_that_is_not_a_single_name(
    tmp_path: Path, name: str
) -> None:
    """Dùng cho mã phiên bản và hash asset — cả hai đều là dữ liệu không tin được.

    Đo trước khi vá: `version_json("/tuyet-doi")` cho ra `/tuyet-doi.json`, tức ghi hẳn ra
    ngoài thư mục dữ liệu.
    """
    with pytest.raises(UnsafePathError):
        resolve_child(tmp_path, name)


@pytest.mark.parametrize(
    "name", ["1.20.1", "1.20.1-forge-47.4.10", "fabric-loader-0.19.3-1.21.4", "a.b_c-d"]
)
def test_resolve_child_allows_real_version_identifiers(tmp_path: Path, name: str) -> None:
    assert resolve_child(tmp_path, name) == tmp_path / name
