"""Điểm vào của lệnh `mccore`.

Khung lệnh dựng sẵn ở bước 1; các lệnh con (version, install, java, account, play,
doctor) được gắn dần vào từ bước 5 trở đi, mỗi bước một PR.
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
    parser.add_subparsers(dest="command", metavar="<lệnh>")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Chạy CLI. Trả về mã thoát (0 là thành công)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    parser.error(f"lệnh chưa được cài đặt: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
