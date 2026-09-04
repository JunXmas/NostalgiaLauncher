"""Soi một bản cài và chỉ ra đúng mắt xích hỏng.

**Cách làm: chạy lại chính những hàm lập kế hoạch của `install/`, nhưng KIỂM thay vì TẢI.**
Nhờ vậy hiểu biết "bản cài đầy đủ gồm những gì" chỉ tồn tại ở một chỗ. Viết riêng một danh
sách cần-có cho `doctor` là cách chắc chắn để một ngày nào đó nó báo thiếu một file mà bộ
cài không bao giờ tải, hoặc bỏ sót một file mà bộ cài có tải.

Phân biệt **chặn** và **cảnh báo** dựa trên một câu hỏi duy nhất: thiếu thứ này thì game có
chạy được không?

- Thiếu client.jar, thư viện, natives, hay bản Java → game **không chạy**. Chặn.
- Thiếu một object asset → game vẫn chạy, chỉ mất một âm thanh hay một chữ. Cảnh báo.
- Thiếu chính chỉ mục asset → không kiểm được gì cả, và đời cũ cần nó để dựng cây tên. Chặn.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from nostalgia.install.assets import plan_asset_index_task, plan_asset_tasks
from nostalgia.install.client import plan_client_task
from nostalgia.install.library import NativeArchive, plan_libraries
from nostalgia.install.natives import iter_native_targets
from nostalgia.model.asset_index import AssetIndex
from nostalgia.model.download import DownloadTask
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import sha1_of_file
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.version.meta import VersionMeta

MISSING = "thiếu"
WRONG_SIZE = "sai kích thước"
WRONG_HASH = "sai sha1"
NOT_EXECUTABLE = "không có cờ thực thi"

CLIENT_JAR = "client.jar"
LIBRARY = "thư viện"
NATIVES = "natives"
ASSET_INDEX = "chỉ mục asset"
ASSET = "asset"
JAVA = "bản Java"


@dataclass(frozen=True, slots=True)
class Finding:
    """Một thứ không ổn. `is_fatal` trả lời: thiếu nó thì game có chạy được không."""

    part: str
    path: Path
    problem: str
    is_fatal: bool


@dataclass(frozen=True, slots=True)
class Diagnosis:
    """Kết quả soi. `checked` để phân biệt "sạch" với "chưa soi gì cả"."""

    findings: tuple[Finding, ...]
    checked: int

    @property
    def is_healthy(self) -> bool:
        return not self.fatal_findings

    @property
    def fatal_findings(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.is_fatal)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if not finding.is_fatal)


def diagnose(
    version_meta: VersionMeta,
    platform: Platform,
    paths: DataPaths,
    *,
    asset_index: AssetIndex | None = None,
    java_binary: Path | None = None,
    verify_hashes: bool = False,
    cancel_token: CancelToken | None = None,
) -> Diagnosis:
    """Soi toàn bộ bản cài của một phiên bản.

    `verify_hashes` băm lại từng file. Đắt — cỡ 1,3 giây cho một bản cài đầy đủ so với
    khoảng 100 ms khi chỉ xem kích thước — nên mặc định tắt, và chỉ nó mới bắt được file bị
    sửa đúng bằng số byte cũ.
    """
    findings: list[Finding] = []
    checked = 0
    for expected in _iter_expected(version_meta, platform, paths, asset_index, java_binary):
        _raise_if_cancelled(cancel_token)
        checked += 1
        findings += _check(expected, verify_hashes=verify_hashes)
    return Diagnosis(findings=tuple(findings), checked=checked)


def remove_broken_files(diagnosis: Diagnosis) -> tuple[Path, ...]:
    """Xoá đúng những file hỏng để lần cài sau tải lại chúng.

    Chỉ xoá file **đã có mà sai**; thứ đang thiếu thì không có gì để xoá. Không đụng tới thư
    mục, và không bao giờ xoá theo kiểu quét cả cây — sửa chữa mà xoá nhầm còn tệ hơn hỏng.
    """
    removed: list[Path] = []
    for finding in diagnosis.findings:
        if finding.problem == MISSING:
            continue
        try:
            finding.path.unlink()
        except OSError:
            continue
        removed.append(finding.path)
    return tuple(removed)


@dataclass(frozen=True, slots=True)
class _Expected:
    """Một file đáng lẽ phải có, kèm cách xác minh nó."""

    part: str
    path: Path
    size: int | None = None
    sha1: str | None = None
    is_fatal: bool = True
    must_be_executable: bool = False


def _iter_expected(
    version_meta: VersionMeta,
    platform: Platform,
    paths: DataPaths,
    asset_index: AssetIndex | None,
    java_binary: Path | None,
) -> Iterator[_Expected]:
    """Danh sách cần-có, sinh ra từ CHÍNH các hàm lập kế hoạch của `install/`."""
    client_task = plan_client_task(version_meta, paths)
    if client_task is not None:
        yield _from_task(CLIENT_JAR, client_task)

    library_plan = plan_libraries(version_meta, platform, paths)
    for task in library_plan.downloads:
        yield _from_task(LIBRARY, task)

    natives_dir = paths.natives_dir(version_meta.version_id)
    for name, size in _native_targets(library_plan.natives_to_extract):
        yield _Expected(part=NATIVES, path=natives_dir / name, size=size)

    if version_meta.asset_index is not None:
        yield _from_task(ASSET_INDEX, plan_asset_index_task(version_meta.asset_index, paths))
    if asset_index is not None:
        for task in plan_asset_tasks(asset_index, paths):
            yield _from_task(ASSET, task, is_fatal=False)

    if java_binary is not None:
        yield _Expected(part=JAVA, path=java_binary, must_be_executable=True)


def _from_task(part: str, task: DownloadTask, *, is_fatal: bool = True) -> _Expected:
    return _Expected(
        part=part, path=task.destination, size=task.size, sha1=task.sha1, is_fatal=is_fatal
    )


def _native_targets(archives: tuple[NativeArchive, ...]) -> tuple[tuple[str, int], ...]:
    """Archive chưa tải về thì bỏ qua — phần thư viện đã báo thiếu nó rồi."""
    try:
        return tuple(iter_native_targets(archives))
    except OSError:
        return ()


def _check(expected: _Expected, *, verify_hashes: bool) -> list[Finding]:
    try:
        actual_size = expected.path.stat().st_size
    except OSError:
        return [_finding(expected, MISSING)]
    if expected.size is not None and actual_size != expected.size:
        return [_finding(expected, WRONG_SIZE)]
    if expected.must_be_executable and not os.access(expected.path, os.X_OK):
        return [_finding(expected, NOT_EXECUTABLE)]
    if verify_hashes and expected.sha1 is not None and sha1_of_file(expected.path) != expected.sha1:
        return [_finding(expected, WRONG_HASH)]
    return []


def _finding(expected: _Expected, problem: str) -> Finding:
    return Finding(
        part=expected.part, path=expected.path, problem=problem, is_fatal=expected.is_fatal
    )


def _raise_if_cancelled(cancel_token: CancelToken | None) -> None:
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
