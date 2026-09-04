"""`nostalgia version` — liệt kê phiên bản.

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
    parser = subparsers.add_parser("version", help="liệt kê phiên bản Minecraft")
    parser.add_argument(
        "--installed", action="store_true", help="chỉ những bản đã có trên đĩa (không cần mạng)"
    )
    parser.add_argument("--limit", type=int, default=20, help="số bản mới nhất hiển thị")
    parser.set_defaults(run=run)


def run(arguments: argparse.Namespace, context: CliContext) -> int:
    from nostalgia.cli.output import say
    from nostalgia.net.http import HttpClient
    from nostalgia.repo.version_repo import VersionRepository

    repository = VersionRepository(context.paths)
    if arguments.installed:
        for version_id in repository.list_installed():
            say(version_id)
        return 0

    with HttpClient() as http_client:
        manifest = VersionRepository(context.paths, http_client).fetch_manifest()
    installed = set(repository.list_installed())
    for manifest_entry in manifest.released()[: max(arguments.limit, 0)]:
        mark = "*" if manifest_entry.version_id in installed else " "
        say(f"{mark} {manifest_entry.version_id}")
    say(f"(mới nhất: {manifest.latest_release_id}; dấu * là đã cài)")
    return 0
