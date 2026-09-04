"""Dựng bản Java trên đĩa: bung lzma, tạo liên kết, đặt cờ thực thi."""

from __future__ import annotations

import lzma
import os
import stat
from pathlib import Path

import pytest

from mccore.errors import Cancelled, IntegrityError
from mccore.java.runtime_plan import CompressedFile, RuntimeLink
from mccore.java.unpack import (
    CHUNK_BYTES,
    LZMA_FORMAT,
    apply_executable_bits,
    create_directories,
    create_links,
    decode_compressed,
)
from mccore.operations.cancellation import CancelToken
from mccore.operations.progress import Progress

CONTENT = b"noi dung that cua mot file trong ban Java\n" * 64


def sha1_of(payload: bytes) -> str:
    import hashlib

    return hashlib.sha1(payload).hexdigest()


def make_archive(directory: Path, name: str, payload: bytes = CONTENT) -> CompressedFile:
    """Nén đúng định dạng Mojang dùng: LZMA "alone", không phải .xz."""
    archive_path = directory / f"{name}.lzma"
    archive_path.write_bytes(lzma.compress(payload, format=LZMA_FORMAT))
    return CompressedFile(
        archive_path=archive_path,
        destination=directory / name,
        sha1=sha1_of(payload),
        size=len(payload),
    )


def test_decoding_restores_the_exact_bytes_and_removes_the_archive(tmp_path: Path) -> None:
    archive = make_archive(tmp_path, "rt.jar")

    written = decode_compressed([archive])

    assert archive.destination.read_bytes() == CONTENT
    assert written == len(CONTENT)
    assert not archive.archive_path.exists(), "để lại bản nén là để lại rác gấp đôi dung lượng"


def test_decoding_creates_missing_parent_directories(tmp_path: Path) -> None:
    """Đích nằm sâu trong cây mà thư mục chưa có: bung phải tự tạo, không được bỏ cuộc."""
    staged = make_archive(tmp_path, "libjsig.so")
    archive = CompressedFile(
        archive_path=staged.archive_path,
        destination=tmp_path / "lib" / "amd64" / "libjsig.so",
        sha1=staged.sha1,
        size=staged.size,
    )

    decode_compressed([archive])

    assert archive.destination.read_bytes() == CONTENT


def test_a_corrupted_archive_leaves_no_file_behind(tmp_path: Path) -> None:
    """Bản Java thiếu một file thì không chạy; ghi ra file sai còn tệ hơn vì trông như xong."""
    archive = make_archive(tmp_path, "rt.jar")
    wrong = CompressedFile(
        archive_path=archive.archive_path,
        destination=archive.destination,
        sha1="0" * 40,
        size=archive.size,
    )

    with pytest.raises(IntegrityError, match="sha1"):
        decode_compressed([wrong])

    assert not archive.destination.exists()
    assert not list(tmp_path.glob(".*")), "không được để lại file tạm"


def test_a_truncated_archive_is_caught_by_size(tmp_path: Path) -> None:
    archive = make_archive(tmp_path, "rt.jar")
    assert archive.size is not None
    lying = CompressedFile(
        archive_path=archive.archive_path,
        destination=archive.destination,
        sha1=None,
        size=archive.size + 1,
    )

    with pytest.raises(IntegrityError, match="byte"):
        decode_compressed([lying])


def test_decoding_reports_progress_and_can_be_cancelled(tmp_path: Path) -> None:
    archives = [make_archive(tmp_path, f"file{index}") for index in range(4)]
    seen: list[Progress] = []

    decode_compressed(archives, workers=2, on_progress=seen.append)

    assert seen[0].done == 0
    assert seen[-1].done == seen[-1].total == 4
    assert [step.done for step in seen] == sorted(step.done for step in seen)

    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        decode_compressed([make_archive(tmp_path, "sau")], cancel_token=cancel_token)


class CancelAfter(CancelToken):
    """Cờ dừng tự bật sau đúng `calls` lần được hỏi — để kiểm việc kiểm cờ có ĐỦ DÀY không."""

    __slots__ = ("_remaining",)

    def __init__(self, calls: int) -> None:
        super().__init__()
        self._remaining = calls

    def raise_if_cancelled(self) -> None:
        if self._remaining <= 0:
            self.cancel()
        self._remaining -= 1
        super().raise_if_cancelled()


def test_cancelling_stops_in_the_middle_of_a_large_file(tmp_path: Path) -> None:
    """File lớn nhất trong một bản Java là `lib/modules` cỡ 130 MB.

    Chỉ kiểm cờ một lần lúc bắt đầu thì nút dừng không có tác dụng gì với nó — người dùng
    bấm dừng rồi vẫn phải ngồi đợi. Dữ liệu ngẫu nhiên để lzma không nén được, nhờ vậy chắc
    chắn có nhiều hơn một khối đọc.
    """
    incompressible = os.urandom(2 * CHUNK_BYTES + 1)
    archive = make_archive(tmp_path, "modules", incompressible)

    with pytest.raises(Cancelled):
        decode_compressed([archive], cancel_token=CancelAfter(2))

    assert not archive.destination.exists()
    assert not [path for path in tmp_path.iterdir() if path.name.startswith(".")]


def test_decoding_nothing_is_not_an_error(tmp_path: Path) -> None:
    assert decode_compressed([]) == 0
    create_directories([])
    create_links([])
    apply_executable_bits([])
    assert not list(tmp_path.iterdir())


def test_empty_directories_are_created_because_the_manifest_declares_them(tmp_path: Path) -> None:
    """Bản thật khai 88 thư mục; thư mục rỗng thì không file nào tạo hộ."""
    directories = [tmp_path / "lib" / "amd64" / "server", tmp_path / "man" / "ja_JP.UTF-8"]

    create_directories(directories)
    assert all(directory.is_dir() for directory in directories)

    create_directories(directories)  # chạy lại không được nổ


def test_links_are_created_relative(tmp_path: Path) -> None:
    (tmp_path / "lib" / "amd64" / "server").mkdir(parents=True)
    (tmp_path / "lib" / "amd64" / "libjsig.so").write_bytes(CONTENT)
    link = RuntimeLink(
        link_path=tmp_path / "lib" / "amd64" / "server" / "libjsig.so",
        target="../libjsig.so",
        resolved_target=tmp_path / "lib" / "amd64" / "libjsig.so",
    )

    create_links([link])

    assert link.link_path.is_symlink()
    assert link.link_path.readlink() == Path("../libjsig.so")
    assert os.fspath(link.link_path.readlink()) == "../libjsig.so"
    assert link.link_path.read_bytes() == CONTENT
    create_links([link])  # chạy lại không được nổ


def test_a_system_without_symlinks_gets_a_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows đòi quyền riêng mới cho tạo symlink — chép là đường lùi đúng, không phải lỗi."""
    (tmp_path / "goc").write_bytes(CONTENT)
    link = RuntimeLink(
        link_path=tmp_path / "ban-sao",
        target="goc",
        resolved_target=tmp_path / "goc",
    )

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError(1, "hệ thống không cho tạo liên kết")

    monkeypatch.setattr(Path, "symlink_to", refuse)
    create_links([link])

    assert not link.link_path.is_symlink()
    assert link.link_path.read_bytes() == CONTENT


def test_executable_bit_is_set_only_where_read_is_allowed(tmp_path: Path) -> None:
    binary = tmp_path / "java"
    binary.write_bytes(b"ELF")
    binary.chmod(0o640)

    apply_executable_bits([binary, tmp_path / "khong-ton-tai"])

    mode = binary.stat().st_mode
    assert mode & stat.S_IXUSR and mode & stat.S_IXGRP
    assert not mode & stat.S_IXOTH, "'other' không đọc được thì cũng không nên chạy được"
