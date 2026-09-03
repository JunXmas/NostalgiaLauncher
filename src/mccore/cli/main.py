"""Điểm vào của lệnh `mccore`.

Bước 1 mới chỉ dựng khung: `--version` và `--help`. Các lệnh con (version, install,
java, account, play, doctor) được gắn dần từ bước 5 trở đi, mỗi bước một PR.
"""

from __future__ import annotations

import argparse
import sys

from mccore import __version__


def build_parser() -> argparse.ArgumentParser:
    """Dựng bộ phân tích đối số. Tách riêng để test gọi được mà không chạy chương trình."""
    parser = argparse.ArgumentParser(
        prog="mccore",
        description="Cài đặt và khởi động Minecraft từ dòng lệnh.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mccore {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Chạy CLI. Trả về mã thoát (0 là thành công)."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
