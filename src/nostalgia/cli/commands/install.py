"""`nostalgia install` — cài đủ một phiên bản.

Mọi thứ nặng được **nạp lười bên trong `run`**. Dựng parser là việc chạy ở MỌI lần gõ lệnh,
kể cả `--help` và `--version`; kéo `http.client`, `ssl`, `zipfile` hay `subprocess` vào lúc
đó là trả giá khởi động cho cả những lệnh không bao giờ dùng tới chúng. Ngân sách ở
`docs/PERFORMANCE.md` phụ thuộc đúng điều này, và có test gác.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nostalgia.cli.context import CliContext


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("install", help="tải đủ một phiên bản về máy")
    parser.add_argument("version_id", help="mã phiên bản, ví dụ 1.20.1")
    parser.add_argument("--game-dir", help="thư mục chạy game (đời cũ cần, để dựng cây asset)")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="xoá những file đã có mà sai, rồi tải lại chúng",
    )
    parser.set_defaults(run=run)


def run(arguments: argparse.Namespace, context: CliContext) -> int:
    from pathlib import Path

    from nostalgia.cli.output import ProgressPrinter, say
    from nostalgia.launch.runner import install_version
    from nostalgia.net.http import HttpClient

    if arguments.repair:
        _repair(arguments, context)

    with HttpClient() as http_client:
        report = install_version(
            arguments.version_id,
            http_client,
            context.paths,
            context.platform,
            game_dir=Path(arguments.game_dir) if arguments.game_dir else None,
            on_progress=ProgressPrinter(quiet=context.quiet),
            cancel_token=context.cancel_token,
        )
    say(
        f"{report.version_meta.version_id}: tải {report.downloaded} file "
        f"({report.bytes_written / 1_000_000:.1f} MB), bỏ qua {report.skipped} file đã đúng"
    )
    say(f"java: {report.java_binary}")
    return 0


def _repair(arguments: argparse.Namespace, context: CliContext) -> None:
    """Chỉ xoá được thứ đã cài; chưa cài gì thì không có gì để sửa."""
    from nostalgia.cli.output import say
    from nostalgia.doctor import diagnose, remove_broken_files
    from nostalgia.repo.version_repo import VersionRepository

    repository = VersionRepository(context.paths)
    if not repository.is_installed(arguments.version_id):
        return
    version_meta = repository.load_version_meta(arguments.version_id)
    diagnosis = diagnose(version_meta, context.platform, context.paths, verify_hashes=True)
    removed = remove_broken_files(diagnosis)
    if removed:
        say(f"đã xoá {len(removed)} file hỏng để tải lại")
