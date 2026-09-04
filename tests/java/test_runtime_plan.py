"""Lập kế hoạch cài bản Java: chọn bản nén, bỏ file đã đúng, chặn đường dẫn thoát ra ngoài."""

from __future__ import annotations

from pathlib import Path

import pytest

from java_fixtures import load_layout_document
from nostalgia.errors import UnsafePathError
from nostalgia.java.runtime_manifest import RuntimeFile, RuntimeLayout, parse_runtime_layout
from nostalgia.java.runtime_plan import ARCHIVE_SUFFIX, plan_runtime
from nostalgia.model.download import RemoteFile


def make_layout(*files: RuntimeFile, links: dict[str, str] | None = None) -> RuntimeLayout:
    return RuntimeLayout(directories=(), files=files, links=links or {})


def make_file(
    relative_path: str, *, size: int = 10, compressed: bool = False, executable: bool = False
) -> RuntimeFile:
    return RuntimeFile(
        relative_path=relative_path,
        raw=RemoteFile(url=f"https://mo/{relative_path}", sha1="a" * 40, size=size),
        compressed=RemoteFile(url=f"https://mo/{relative_path}.lzma", sha1="b" * 40, size=4)
        if compressed
        else None,
        is_executable=executable,
    )


def test_compressed_files_download_the_archive_and_queue_a_decode(tmp_path: Path) -> None:
    """Tải bản nén tiết kiệm 77% băng thông — đo trên bản `jre-legacy` thật: 223 MB xuống 51."""
    plan = plan_runtime(make_layout(make_file("lib/rt.jar", compressed=True)), tmp_path)

    assert [task.url for task in plan.downloads] == ["https://mo/lib/rt.jar.lzma"]
    assert plan.downloads[0].destination == tmp_path / "lib" / ("rt.jar" + ARCHIVE_SUFFIX)
    assert len(plan.archives_to_decode) == 1
    decode = plan.archives_to_decode[0]
    assert decode.destination == tmp_path / "lib" / "rt.jar"
    assert decode.sha1 == "a" * 40, "phải xác minh bằng sha1 của bản THÔ, không phải bản nén"
    assert decode.size == 10


def test_files_without_a_compressed_variant_download_straight_to_place(tmp_path: Path) -> None:
    plan = plan_runtime(make_layout(make_file("release")), tmp_path)
    assert plan.downloads[0].destination == tmp_path / "release"
    assert plan.archives_to_decode == ()


def test_a_file_already_on_disk_is_not_downloaded_again(tmp_path: Path) -> None:
    """Không kiểm ĐÍCH THẬT thì lần cài thứ hai tải lại toàn bộ: bản nén đã bị xoá sau khi bung."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "rt.jar").write_bytes(b"x" * 10)

    plan = plan_runtime(make_layout(make_file("lib/rt.jar", compressed=True)), tmp_path)

    assert plan.downloads == ()
    assert plan.archives_to_decode == ()


def test_a_file_of_the_wrong_size_is_downloaded_again(tmp_path: Path) -> None:
    (tmp_path / "release").write_bytes(b"x" * 9)
    plan = plan_runtime(make_layout(make_file("release", size=10)), tmp_path)
    assert len(plan.downloads) == 1


def test_a_leftover_archive_is_reported_for_cleanup(tmp_path: Path) -> None:
    """Chạy đứt gánh giữa lúc bung xong và lúc xoá sẽ để lại bản nén — phải dọn, không để rác."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "rt.jar").write_bytes(b"x" * 10)
    leftover = tmp_path / "lib" / ("rt.jar" + ARCHIVE_SUFFIX)
    leftover.write_bytes(b"nen")

    plan = plan_runtime(make_layout(make_file("lib/rt.jar", compressed=True)), tmp_path)

    assert plan.stale_archives == (leftover,)


def test_nothing_is_reported_stale_when_there_is_no_leftover(tmp_path: Path) -> None:
    (tmp_path / "release").write_bytes(b"x" * 10)
    plan = plan_runtime(make_layout(make_file("release", compressed=True)), tmp_path)
    assert plan.stale_archives == ()


def test_executables_are_listed_even_when_the_file_is_already_correct(tmp_path: Path) -> None:
    """Cờ thực thi phải được đặt lại mỗi lượt: thiếu nó thì bản Java im lặng không chạy."""
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "java").write_bytes(b"x" * 10)

    plan = plan_runtime(make_layout(make_file("bin/java", executable=True)), tmp_path)

    assert plan.downloads == ()
    assert plan.executables == (tmp_path / "bin" / "java",)


def test_relative_links_pointing_upwards_are_allowed(tmp_path: Path) -> None:
    """Bản thật có `lib/amd64/server/libjsig.so` -> `../libjsig.so`. Cấm `..` là cấm cả bản thật."""
    plan = plan_runtime(
        make_layout(links={"lib/amd64/server/libjsig.so": "../libjsig.so"}), tmp_path
    )
    link = plan.links[0]
    assert link.target == "../libjsig.so", "đưa cho symlink phải là đường TƯƠNG ĐỐI"
    assert link.resolved_target == tmp_path / "lib" / "amd64" / "libjsig.so"


def test_links_escaping_the_runtime_are_refused(tmp_path: Path) -> None:
    with pytest.raises(UnsafePathError, match="trỏ ra ngoài"):
        plan_runtime(make_layout(links={"bin/x": "../../../../etc/passwd"}), tmp_path)


def test_entry_paths_escaping_the_runtime_are_refused(tmp_path: Path) -> None:
    with pytest.raises(UnsafePathError):
        plan_runtime(make_layout(make_file("../../evil.so")), tmp_path)


def test_the_real_manifest_plans_every_entry(tmp_path: Path) -> None:
    plan = plan_runtime(parse_runtime_layout(load_layout_document()), tmp_path)

    assert len(plan.directories) == 5
    assert len(plan.downloads) == 7
    assert len(plan.archives_to_decode) == 5, "5 trong 7 file thật có bản nén"
    assert len(plan.links) == 3
    assert len(plan.executables) == 3
    assert all(path.is_relative_to(tmp_path) for path in plan.directories)
    assert all(task.destination.is_relative_to(tmp_path) for task in plan.downloads)
