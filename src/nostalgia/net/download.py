"""Tải nhiều file song song, xác minh, và tự chữa file hỏng.

Bảy trong chín luật ở docs/PERFORMANCE.md §5 được thi hành ở đây:

- **16 luồng mặc định**, cho phép chỉnh. Đo được: 1 luồng 8,9 file/s, 16 luồng ~92 file/s.
  Trên 16 thì các số đo mâu thuẫn nhau giữa các lượt nên không chốt cao hơn.
- **Giữ kết nối sống** — do `HttpClient` lo, mỗi luồng một kết nối bền.
- **Băm sha1 NGAY TRONG LÚC tải.** Byte đang nằm trong bộ nhớ; sha1 chạy ~500 MB/s còn mạng
  17-33 MB/s, nên băm khi ghi tốn dưới 5% một lõi. Nhờ vậy mọi file được băm đúng một lần
  lúc sinh ra, và việc xác minh lần sau bằng kích thước trở nên ĐÚNG ĐẮN về logic chứ không
  chỉ là đánh đổi rủi ro.
- **Xác minh mặc định bằng kích thước** khi quyết định có bỏ qua file đã có hay không.
- **Ghi nguyên tử**: ra file tạm, `fsync`, rồi `os.replace`, rồi `fsync` thư mục.
- **Trần kích thước và kiểm cờ huỷ sau mỗi khối** — do `HttpClient.stream` thi hành. Không
  có hai thứ đó thì một máy chủ gửi mãi sẽ ghi tới khi hết đĩa, và nút dừng thành vô dụng
  với bản cài 649 MB (đã đo cả hai, xem test trong tests/net/).
- **Dedupe theo đích** trước khi chạy, để hai luồng không cùng ghi vào một file.
- **Bỏ qua file đã đúng** — lần cài thứ hai gần như không phát request nào.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import Cancelled, IntegrityError
from nostalgia.model.download import DownloadTask
from nostalgia.net.http import DEFAULT_RETRY_POLICY, HttpClient, RetryPolicy, retry
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress
from nostalgia.storage.files import DEFAULT_FILE_MODE, ensure_dir, sync_directory

DEFAULT_WORKERS = 16
STAGE = "tải"


@dataclass(frozen=True, slots=True)
class DownloadFailure:
    """Một việc tải đã thất bại, kèm lý do đọc được."""

    task: DownloadTask
    reason: str


@dataclass(frozen=True, slots=True)
class DownloadReport:
    """Kết quả của cả đợt tải.

    Trả về báo cáo thay vì ném ngay ở lỗi đầu tiên: `doctor` cần biết TẤT CẢ những gì thiếu,
    và một lỗi giữa đợt không nên xoá công của 3.000 file đã tải xong.
    """

    downloaded: int
    skipped: int
    bytes_written: int
    failures: tuple[DownloadFailure, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def is_already_correct(task: DownloadTask) -> bool:
    """File đã có và đúng kích thước thì bỏ qua — không băm lại 649 MB mỗi lần cài.

    Băm sha1 ở đây sẽ tốn ~1,3 giây cho một bản cài đầy đủ, so với ~104 ms chỉ `stat`. Việc
    băm đã được làm đúng một lần lúc tải, nên kích thước là đủ cho đường thường ngày; ai
    muốn chắc hơn thì dùng cờ xác minh sâu ở bước 13.
    """
    try:
        actual_size = task.destination.stat().st_size
    except FileNotFoundError:
        return False
    return task.size is None or actual_size == task.size


def download_one(
    http_client: HttpClient,
    task: DownloadTask,
    *,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    cancel_token: CancelToken | None = None,
) -> int:
    """Tải một file nếu cần. Trả về số byte đã ghi; 0 nghĩa là bỏ qua vì đã đúng."""
    if is_already_correct(task):
        return 0
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    ensure_dir(task.destination.parent)
    return retry(
        lambda: _fetch_and_commit(http_client, task, cancel_token),
        policy=retry_policy,
        cancel_token=cancel_token,
    )


def download_all(
    http_client: HttpClient,
    tasks: list[DownloadTask],
    *,
    workers: int = DEFAULT_WORKERS,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
) -> DownloadReport:
    """Tải cả danh sách song song, báo tiến độ, và gom mọi thất bại vào báo cáo."""
    if workers < 1:
        message = f"số luồng phải >= 1, nhận được {workers}"
        raise ValueError(message)

    unique_tasks = _deduplicate(tasks)
    total = len(unique_tasks)
    counter = _ProgressCounter(total, on_progress)
    failures: list[DownloadFailure] = []
    downloaded = skipped = written_total = 0
    failure_lock = threading.Lock()

    def run(task: DownloadTask) -> int:
        try:
            return download_one(
                http_client, task, retry_policy=retry_policy, cancel_token=cancel_token
            )
        except Cancelled:
            raise
        # Bắt rộng có chủ ý: một file lỗi không được làm sập cả đợt 3.500 file. Riêng
        # Cancelled đã được cho nổi lên ở nhánh trên.
        except Exception as exc:
            with failure_lock:
                failures.append(DownloadFailure(task=task, reason=str(exc)))
            return -1
        finally:
            counter.advance()

    counter.report()
    with ThreadPoolExecutor(max_workers=min(workers, total or 1)) as pool:
        for written in pool.map(run, unique_tasks):
            if written < 0:
                continue
            written_total += written
            if written:
                downloaded += 1
            else:
                skipped += 1

    return DownloadReport(
        downloaded=downloaded,
        skipped=skipped,
        bytes_written=written_total,
        failures=tuple(failures),
    )


class _ProgressCounter:
    """Đếm số việc đã xong và gọi callback. Có khoá vì nhiều luồng cùng tăng."""

    __slots__ = ("_done", "_lock", "_on_progress", "_total")

    def __init__(self, total: int, on_progress: ProgressFn) -> None:
        self._total = total
        self._done = 0
        self._on_progress = on_progress
        self._lock = threading.Lock()

    def advance(self) -> None:
        with self._lock:
            self._done += 1
            done = self._done
        self._on_progress(Progress(STAGE, done, self._total))

    def report(self) -> None:
        self._on_progress(Progress(STAGE, self._done, self._total))


def _deduplicate(tasks: list[DownloadTask]) -> list[DownloadTask]:
    """Giữ thứ tự, bỏ việc trùng đích.

    Không chỉ để tiết kiệm: hai luồng cùng ghi vào một đích là điều kiện đua thật sự. Chỉ
    mục asset của 1.20.1 có 23 mục trùng hash.
    """
    seen: set[Path] = set()
    unique_tasks = []
    for task in tasks:
        if task.destination in seen:
            continue
        seen.add(task.destination)
        unique_tasks.append(task)
    return unique_tasks


def _fetch_and_commit(
    http_client: HttpClient, task: DownloadTask, cancel_token: CancelToken | None
) -> int:
    """Tải vào file tạm, băm trong lúc ghi, xác minh, rồi đổi tên nguyên tử.

    File tạm dùng `mkstemp` trong cùng thư mục đích: tên chắc chắn không trùng giữa các
    luồng và các tiến trình, và `os.replace` chỉ nguyên tử trên cùng một hệ thống file.
    """
    digest = hashlib.sha1()
    descriptor, temporary_name = tempfile.mkstemp(
        dir=task.destination.parent, prefix=f".{task.destination.name}."
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:

            def write(chunk: bytes) -> None:
                digest.update(chunk)
                handle.write(chunk)

            written = http_client.stream(
                task.url,
                write,
                expected_size=task.size,
                cancel_token=cancel_token,
            )
            handle.flush()
            os.fsync(handle.fileno())

        _verify(task, written, digest.hexdigest())
        temporary_path.chmod(DEFAULT_FILE_MODE)
        temporary_path.replace(task.destination)
        sync_directory(task.destination.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return written


def _verify(task: DownloadTask, written: int, actual_sha1: str) -> None:
    if task.size is not None and written != task.size:
        message = f"{task.url}: nhận {written} byte, máy chủ công bố {task.size}"
        raise IntegrityError(message)
    if task.sha1 is not None and actual_sha1 != task.sha1:
        message = f"{task.url}: sha1 {actual_sha1}, máy chủ công bố {task.sha1}"
        raise IntegrityError(message)
