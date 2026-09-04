"""Giải nén natives: làm phẳng, tôn trọng `extract.exclude`, và chặn tài nguyên."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from mccore.errors import Cancelled, IntegrityError
from mccore.install.library import NativeArchive
from mccore.install.natives import extract_natives
from mccore.operations.cancellation import CancelToken

LIBRARY_BYTES = b"\x7fELF" + b"n" * 500


def make_archive(path: Path, members: dict[str, bytes]) -> NativeArchive:
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return NativeArchive(archive_path=path, excludes=("META-INF/",))


def test_nested_libraries_are_flattened(tmp_path: Path) -> None:
    """Soi jar thật: `lwjgl-vma` chôn `.so` dưới `linux/x64/org/lwjgl/vma/`.

    JVM không tìm đệ quy trong `java.library.path`, nên giữ nguyên cây là game không nạp
    được thư viện.
    """
    archive = make_archive(
        tmp_path / "a.jar", {"linux/x64/org/lwjgl/vma/liblwjgl_vma.so": LIBRARY_BYTES}
    )
    natives_dir = tmp_path / "natives"
    report = extract_natives((archive,), natives_dir)
    assert (natives_dir / "liblwjgl_vma.so").read_bytes() == LIBRARY_BYTES
    assert report.extracted == (natives_dir / "liblwjgl_vma.so",)


def test_files_already_at_the_root_stay_there(tmp_path: Path) -> None:
    """Đời 1.8.9 để `.so` ngay ở gốc jar — cả hai bố trí phải cùng chạy."""
    archive = make_archive(tmp_path / "a.jar", {"liblwjgl.so": LIBRARY_BYTES})
    natives_dir = tmp_path / "natives"
    extract_natives((archive,), natives_dir)
    assert (natives_dir / "liblwjgl.so").read_bytes() == LIBRARY_BYTES


def test_excluded_prefixes_are_skipped(tmp_path: Path) -> None:
    archive = make_archive(
        tmp_path / "a.jar",
        {
            "META-INF/MANIFEST.MF": b"x",
            "META-INF/linux/x64/liblwjgl.so.sha1": b"y",
            "liblwjgl.so": LIBRARY_BYTES,
        },
    )
    natives_dir = tmp_path / "natives"
    extract_natives((archive,), natives_dir)
    assert sorted(path.name for path in natives_dir.iterdir()) == ["liblwjgl.so"]


def test_running_twice_changes_nothing(tmp_path: Path) -> None:
    archive = make_archive(tmp_path / "a.jar", {"liblwjgl.so": LIBRARY_BYTES})
    natives_dir = tmp_path / "natives"
    first = extract_natives((archive,), natives_dir)
    second = extract_natives((archive,), natives_dir)
    assert len(first.extracted) == 1
    assert second.extracted == ()
    assert second.skipped_unchanged == 1


def test_two_archives_claiming_one_name_with_different_content_is_an_error(
    tmp_path: Path,
) -> None:
    """Ghi đè lặng lẽ là cách tệ nhất: game nạp nhầm thư viện và lỗi hiện ra ở chỗ khác."""
    first = make_archive(tmp_path / "a.jar", {"deep/liblwjgl.so": LIBRARY_BYTES})
    second = make_archive(tmp_path / "b.jar", {"other/liblwjgl.so": LIBRARY_BYTES + b"khac"})
    with pytest.raises(IntegrityError, match="cùng đòi tên"):
        extract_natives((first, second), tmp_path / "natives")


def test_the_same_file_from_two_archives_is_fine(tmp_path: Path) -> None:
    """Cùng tên, cùng kích thước thì không phải xung đột — chỉ là bung lại."""
    first = make_archive(tmp_path / "a.jar", {"x/liblwjgl.so": LIBRARY_BYTES})
    second = make_archive(tmp_path / "b.jar", {"y/liblwjgl.so": LIBRARY_BYTES})
    report = extract_natives((first, second), tmp_path / "natives")
    assert report.skipped_unchanged == 1


def test_a_path_that_tries_to_escape_is_neutralised(tmp_path: Path) -> None:
    """Làm phẳng vô hiệu hoá zip-slip theo cấu trúc, nhưng vẫn kiểm lại tên cuối."""
    archive = make_archive(tmp_path / "a.jar", {"../../../../etc/passwd": b"x"})
    natives_dir = tmp_path / "natives"
    extract_natives((archive,), natives_dir)
    assert [path.name for path in natives_dir.iterdir()] == ["passwd"]
    assert not (tmp_path.parent / "passwd").exists()


def test_extraction_stops_at_the_size_ceiling(tmp_path: Path) -> None:
    """Một archive khai dung lượng bung khổng lồ không được làm đầy đĩa."""
    archive = make_archive(tmp_path / "a.jar", {"big.so": b"z" * 100_000})
    with pytest.raises(IntegrityError, match="bung quá"):
        extract_natives((archive,), tmp_path / "natives", max_extracted_bytes=1000)


def test_cancellation_is_honoured(tmp_path: Path) -> None:
    archive = make_archive(tmp_path / "a.jar", {"liblwjgl.so": LIBRARY_BYTES})
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        extract_natives((archive,), tmp_path / "natives", cancel_token=cancel_token)


def test_directory_entries_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "a.jar"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("linux/", b"")
        archive.writestr("linux/liblwjgl.so", LIBRARY_BYTES)
    natives_dir = tmp_path / "natives"
    extract_natives((NativeArchive(archive_path=path),), natives_dir)
    assert [path.name for path in natives_dir.iterdir()] == ["liblwjgl.so"]


def test_an_empty_archive_list_creates_the_directory(tmp_path: Path) -> None:
    natives_dir = tmp_path / "natives"
    report = extract_natives((), natives_dir)
    assert natives_dir.is_dir()
    assert report.extracted == ()


def test_meta_inf_is_dropped_even_when_the_version_declares_nothing(tmp_path: Path) -> None:
    """Thư viện natives đời ≥1.19 KHÔNG khai `extract.exclude` — Mojang chỉ khai ở đời cũ.

    Chỉ nghe theo khai báo thì `META-INF/MANIFEST.MF` bị bung từ mọi jar và đụng nhau ngay.
    Đã gặp thật khi chạy trên jar thật của 1.21.4, không lộ ra với jar dựng trong test.
    """
    first = tmp_path / "a.jar"
    second = tmp_path / "b.jar"
    for path, payload in ((first, b"manifest a"), (second, b"manifest b khac")):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", payload)
            archive.writestr(f"{path.stem}/lib{path.stem}.so", LIBRARY_BYTES)

    natives_dir = tmp_path / "natives"
    extract_natives(
        (NativeArchive(archive_path=first), NativeArchive(archive_path=second)), natives_dir
    )
    assert sorted(path.name for path in natives_dir.iterdir()) == ["liba.so", "libb.so"]
