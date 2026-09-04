"""Chạy game và dừng game — kể cả khi nó đẻ ra cả cây tiến trình con.

**Luật số một: không bao giờ tự giết chính mình.** `os.killpg` giết cả nhóm tiến trình; nếu
game chạy chung nhóm với launcher thì một cú "Dừng" là tắt luôn launcher, và trên máy chủ
CI là tắt luôn cả bộ test. Vì thế game được đặt vào **phiên riêng** (`start_new_session`),
và trước khi gửi tín hiệu cho cả nhóm, mã còn kiểm lại `pgid == pid` — chỉ nhóm nào do
chính game làm trưởng nhóm mới bị đụng tới.

**Luật số hai: không vòng lặp nào chờ mãi.** Ba chỗ có thể treo vĩnh viễn, mỗi chỗ một hạn:

- tiến trình lờ `SIGTERM` → hết hạn ân huệ thì `SIGKILL`;
- cháu nội giữ ống `stdout` sau khi cha đã thoát → luồng đọc là luồng nền, và `wait` chỉ
  đợi nó một hạn ngắn rồi thôi (nếu chờ EOF thì treo mãi mãi);
- `wait` sau `SIGKILL` cũng có hạn, để một tiến trình zombie không kéo theo cả launcher.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
from collections.abc import Callable, Mapping

from nostalgia.launch.command import LaunchCommand
from nostalgia.storage.files import ensure_dir

type OutputFn = Callable[[str], None]

# Hạn ân huệ cho game tự đóng sau SIGTERM. Minecraft cần lưu thế giới trước khi thoát; 3 giây
# đủ cho thao tác đó, và cộng với hạn dưới thì `stop()` luôn trả về trong 5 giây.
DEFAULT_GRACE_SECONDS = 3.0

# Sau SIGKILL thì nhân hệ điều hành thu dọn gần như tức thì; hạn này chỉ để không chờ mãi
# trong trường hợp tiến trình kẹt ở trạng thái không ngắt được.
KILL_WAIT_SECONDS = 2.0

# Chờ luồng đọc gom nốt output. Cháu nội giữ ống có thể khiến nó không bao giờ thấy EOF.
OUTPUT_DRAIN_SECONDS = 2.0

logger = logging.getLogger(__name__)


# Hai cách gửi tín hiệu, và cách chọn giữa chúng. Tách ra thành hàm THUẦN vì đây là quyết
# định an toàn quan trọng nhất của module mà không thể kiểm bằng cách gửi tín hiệu thật:
# kiểm kiểu đó nghĩa là cố tình bắn vào nhóm tiến trình đang chạy chính bộ test.
WHOLE_GROUP = "group"
SINGLE_PROCESS = "process"


def resolve_signal_target(pid: int, process_group: int) -> tuple[str, int]:
    """Được phép giết cả nhóm hay chỉ một tiến trình.

    Chỉ giết cả nhóm khi tiến trình CHÍNH LÀ trưởng nhóm — khi đó nhóm đó là phiên riêng do
    `start_new_session` tạo ra, chắc chắn không chứa launcher. Mọi trường hợp khác thì thà
    bỏ sót tiến trình cháu còn hơn giết nhầm nhóm đang chứa chính mình.
    """
    if process_group == pid:
        return WHOLE_GROUP, process_group
    return SINGLE_PROCESS, pid


def ignore_output(_line: str) -> None:
    """Mặc định: bỏ output đi. Lõi không in ra màn hình — đó là việc của `cli/`."""


class GameProcess:
    """Một tiến trình game đang chạy. Không tự sinh luồng nào ngoài luồng đọc output."""

    __slots__ = ("_output_thread", "_process")

    def __init__(self, process: subprocess.Popen[bytes], on_output: OutputFn) -> None:
        self._process = process
        self._output_thread = threading.Thread(
            target=_pump_output, args=(process, on_output), daemon=True
        )
        self._output_thread.start()

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def exit_code(self) -> int | None:
        """`None` nghĩa là còn chạy. Có gọi `poll` nên giá trị luôn tươi."""
        return self._process.poll()

    @property
    def is_running(self) -> bool:
        return self.exit_code is None

    def wait(self, timeout: float | None = None) -> int:
        """Đợi game thoát và trả về mã thoát.

        Sau khi tiến trình chết vẫn đợi thêm một hạn NGẮN cho luồng đọc gom nốt output —
        chờ nó vô hạn là treo cả launcher khi có cháu nội giữ ống.
        """
        exit_code = self._process.wait(timeout=timeout)
        self._output_thread.join(timeout=OUTPUT_DRAIN_SECONDS)
        return exit_code

    def stop(self, *, grace_seconds: float = DEFAULT_GRACE_SECONDS) -> int:
        """Xin game tự đóng, rồi ép nếu nó không chịu. Luôn trả về trong vài giây.

        Gọi khi game đã thoát là vô hại — và quan trọng hơn, **không gửi tín hiệu nào**.
        Sau khi tiến trình được thu dọn, số pid của nó có thể được cấp lại cho tiến trình
        khác; bắn tín hiệu vào đó là giết nhầm một chương trình không liên quan.
        """
        exit_code = self._process.poll()
        if exit_code is not None:
            self._output_thread.join(timeout=OUTPUT_DRAIN_SECONDS)
            return exit_code

        self._signal(signal.SIGTERM)
        try:
            return self.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            logger.warning("game (pid %d) không đóng sau SIGTERM, chuyển sang SIGKILL", self.pid)

        self._signal(signal.SIGKILL)
        return self.wait(timeout=KILL_WAIT_SECONDS)

    def _signal(self, sent_signal: signal.Signals) -> None:
        """Gửi tín hiệu cho CẢ CÂY tiến trình, nhưng chỉ khi chắc chắn không đụng chính mình."""
        pid = self._process.pid
        try:
            process_group = os.getpgid(pid)
        except (ProcessLookupError, PermissionError):
            return
        try:
            if process_group == pid:
                # Game là trưởng nhóm phiên riêng của nó: giết cả nhóm là giết cả cây con,
                # và chắc chắn không chạm tới nhóm của launcher.
                os.killpg(process_group, sent_signal)
            else:
                # Không nên xảy ra, nhưng nếu xảy ra thì thà bỏ sót tiến trình cháu còn hơn
                # giết nhầm cả nhóm đang chứa launcher.
                logger.warning(
                    "pid %d không phải trưởng nhóm %d, chỉ giết một mình nó", pid, process_group
                )
                os.kill(pid, sent_signal)
        except ProcessLookupError:
            return


def start_game(
    command: LaunchCommand,
    *,
    on_output: OutputFn = ignore_output,
    environment: Mapping[str, str] | None = None,
) -> GameProcess:
    """Chạy lệnh đã dựng, trong thư mục game, ở một phiên riêng."""
    ensure_dir(command.game_dir)
    process = subprocess.Popen(
        command.argv,
        cwd=command.game_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        env=dict(environment) if environment is not None else None,
        start_new_session=True,
    )
    return GameProcess(process, on_output)


def _pump_output(process: subprocess.Popen[bytes], on_output: OutputFn) -> None:
    """Đọc output theo dòng cho tới EOF. Chạy trong luồng nền.

    Hai lớp chống mất log, vì log là thứ người dùng cần đúng lúc mọi thứ đang hỏng:

    - Giải mã với `errors="replace"`: log của game có thể chứa byte không phải UTF-8 (tên
      file, thư viện của mod), và một `UnicodeDecodeError` sẽ giết luồng đọc.
    - Lỗi từ `on_output` là lỗi của NGƯỜI GỌI, không phải của game. Ghi lại rồi đọc tiếp;
      để nó thoát ra là mất toàn bộ phần log còn lại vì một lỗi ở chỗ khác.
    """
    stream = process.stdout
    if stream is None:
        return
    try:
        for raw_line in stream:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            try:
                on_output(line)
            except Exception:
                logger.exception("bộ nhận output của người gọi ném lỗi, bỏ qua dòng này")
    except (OSError, ValueError):
        return
    finally:
        stream.close()
