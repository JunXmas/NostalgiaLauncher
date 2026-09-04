"""Điểm vào của lệnh `nostalgia`.

Tầng này và chỉ tầng này được phép in ra màn hình và đọc biến môi trường. Mọi lệnh con nhận
một `CliContext` dựng sẵn — không có đường dẫn mặc định ẩn nào nằm rải trong code.

Ctrl+C **không** giết ngay: nó đặt cờ huỷ, để phần đang chạy dọn dẹp tử tế (xoá file tải dở,
xin game tự đóng và lưu thế giới). Bấm lần thứ hai mới ép thoát.

Ngay cả `CliContext` cũng nạp lười: nó kéo theo `dataclasses`, và `dataclasses` kéo theo
`inspect`. Đo được riêng chuỗi đó tốn hơn một lần khởi động Python trần, trả cho cả những
lệnh chỉ in trợ giúp. Có test và có bench gác con số này.
"""

from __future__ import annotations

import argparse
import signal
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType

    from nostalgia.operations.cancellation import CancelToken

from nostalgia import __version__
from nostalgia.cli.commands import account, doctor, install, play, version

if TYPE_CHECKING:
    pass

CANCELLED_EXIT_CODE = 130
ERROR_EXIT_CODE = 1


def build_parser() -> argparse.ArgumentParser:
    """Dựng bộ phân tích đối số. Tách riêng để test gọi được mà không chạy chương trình."""
    parser = argparse.ArgumentParser(
        prog="nostalgia",
        description="Nostalgia Launcher — cài đặt và khởi động Minecraft từ dòng lệnh.",
    )
    parser.add_argument("--version", action="version", version=f"nostalgia {__version__}")
    parser.add_argument("--data-dir", help="thư mục kho (mặc định theo quy ước hệ điều hành)")
    parser.add_argument("--config-dir", help="thư mục cấu hình")
    parser.add_argument("-q", "--quiet", action="store_true", help="không in tiến độ và log game")

    subparsers = parser.add_subparsers(dest="command")
    for module in (version, install, doctor, account, play):
        module.add_parser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Chạy CLI. 0 là xong, 1 là lỗi, 130 là người dùng bấm dừng."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if getattr(arguments, "run", None) is None:
        parser.print_help()
        return 0

    from nostalgia.cli.context import CliContext
    from nostalgia.cli.output import fail, warn
    from nostalgia.errors import Cancelled, NostalgiaError
    from nostalgia.operations.cancellation import CancelToken

    cancel_token = CancelToken()
    _install_cancel_handler(cancel_token)
    context = CliContext.build(
        data_dir=arguments.data_dir,
        config_dir=arguments.config_dir,
        quiet=arguments.quiet,
        cancel_token=cancel_token,
    )
    try:
        return int(arguments.run(arguments, context))
    except Cancelled:
        warn("đã dừng theo yêu cầu")
        return CANCELLED_EXIT_CODE
    except KeyboardInterrupt:
        return CANCELLED_EXIT_CODE
    except NostalgiaError as error:
        fail(str(error))
        return ERROR_EXIT_CODE


def _install_cancel_handler(cancel_token: CancelToken) -> None:
    """Ctrl+C lần đầu đặt cờ huỷ; lần thứ hai để mặc định ép thoát.

    Không khôi phục hành vi mặc định ở lần hai thì một chỗ nào đó lỡ không kiểm cờ sẽ khiến
    người dùng không thoát nổi — nút dừng phải luôn có đường thoát cuối.
    """

    def handle(_signal_number: int, _frame: FrameType | None) -> None:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        cancel_token.cancel()

    try:
        signal.signal(signal.SIGINT, handle)
    except ValueError:
        # Không ở luồng chính (ví dụ bị gọi từ giao diện): bỏ qua, người gọi tự lo việc huỷ.
        return


if __name__ == "__main__":
    sys.exit(main())
