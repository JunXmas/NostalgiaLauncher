"""`nostalgia doctor` — soi một bản cài và chỉ ra mắt xích hỏng.

Mọi thứ nặng được **nạp lười bên trong `run`** — xem `cli/commands/version.py` để biết lý do.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nostalgia.cli.context import CliContext


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("doctor", help="soi một bản cài")
    parser.add_argument("version_id", help="mã phiên bản, ví dụ 1.20.1")
    parser.add_argument(
        "--verify-hashes",
        action="store_true",
        help="băm lại từng file; chậm hơn nhiều nhưng bắt được file bị sửa đúng bằng số byte cũ",
    )
    parser.set_defaults(run=run)


def run(arguments: argparse.Namespace, context: CliContext) -> int:
    """Thiếu thứ CHẶN thì trả về 1; chỉ có cảnh báo thì vẫn trả về 0."""
    from nostalgia.cli.output import print_diagnosis, say, warn
    from nostalgia.doctor import diagnose
    from nostalgia.install.assets import load_installed_asset_index
    from nostalgia.launch.runner import resolve_installed_java_binary
    from nostalgia.repo.version_repo import VersionRepository

    repository = VersionRepository(context.paths)
    version_id = arguments.version_id
    if not repository.is_installed(version_id):
        warn(f"  ✗ không có {context.paths.version_json(version_id)}")
        say(f"{version_id}: chưa cài — chạy `nostalgia install {version_id}`")
        return 1

    version_meta = repository.load_version_meta(version_id)
    diagnosis = diagnose(
        version_meta,
        context.platform,
        context.paths,
        asset_index=load_installed_asset_index(version_meta, context.paths),
        java_binary=resolve_installed_java_binary(version_meta, context.platform, context.paths),
        verify_hashes=arguments.verify_hashes,
        cancel_token=context.cancel_token,
    )
    print_diagnosis(diagnosis, version_id)
    return 0 if diagnosis.is_healthy else 1
