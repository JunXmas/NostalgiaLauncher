"""`nostalgia instance` — tạo, liệt kê, xoá bản chơi.

Mọi thứ nặng được **nạp lười bên trong `run`** — xem `cli/commands/version.py` để biết lý do.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nostalgia.cli.context import CliContext


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("instance", help="quản lý bản chơi")
    actions = parser.add_subparsers(dest="instance_action", required=True)

    create = actions.add_parser("create", help="tạo một bản chơi mới")
    create.add_argument("instance_id", help="mã bản chơi, ví dụ vui-ve")
    create.add_argument("--version", required=True, help="mã phiên bản, ví dụ 1.20.1")
    create.add_argument("--name", default="", help="tên hiển thị (mặc định: dùng mã)")
    create.add_argument("--max-memory", type=int, default=None, help="bộ nhớ tối đa, tính MB")
    create.add_argument("--width", type=int, default=None, help="chiều rộng cửa sổ")
    create.add_argument("--height", type=int, default=None, help="chiều cao cửa sổ")
    create.add_argument(
        "--game-dir", default="", help="thư mục chơi riêng (vd ổ khác); mặc định instances/<mã>"
    )
    create.set_defaults(run=run_create)

    actions.add_parser("list", help="liệt kê bản chơi").set_defaults(run=run_list)

    remove = actions.add_parser("remove", help="gỡ một bản chơi (mặc định GIỮ thế giới)")
    remove.add_argument("instance_id")
    remove.add_argument(
        "--delete-worlds",
        action="store_true",
        help="xoá luôn thư mục chơi, kể cả thế giới đã lưu — không lấy lại được",
    )
    remove.set_defaults(run=run_remove)

    parser.set_defaults(run=run_list)


def run_create(arguments: argparse.Namespace, context: CliContext) -> int:
    from nostalgia.cli.output import say
    from nostalgia.instance.model import Instance
    from nostalgia.instance.store import check_game_dir_override, create_instance, game_dir_of

    instance = create_instance(
        context.paths,
        Instance(
            instance_id=arguments.instance_id,
            version_id=arguments.version,
            display_name=arguments.name,
            max_heap_megabytes=arguments.max_memory,
            window_width=arguments.width,
            window_height=arguments.height,
            game_dir_override=check_game_dir_override(context.paths, arguments.game_dir),
        ),
    )
    say(f"đã tạo {instance.label} ({instance.version_id})")
    say(f"thư mục chơi: {game_dir_of(context.paths, instance)}")
    return 0


def run_list(_arguments: argparse.Namespace, context: CliContext) -> int:
    from nostalgia.cli.output import say
    from nostalgia.instance.store import list_instances

    instances = list_instances(context.paths)
    if not instances:
        say("chưa có bản chơi nào — chạy `nostalgia instance create <tên> --version 1.20.1`")
        return 0
    for instance in instances:
        say(f"{instance.instance_id}  {instance.version_id}  {instance.label}")
    return 0


def run_remove(arguments: argparse.Namespace, context: CliContext) -> int:
    """Mặc định giữ thế giới. Xoá là việc phải nói rõ, không phải mặc định."""
    import shutil

    from nostalgia.cli.output import say
    from nostalgia.instance.store import unregister_instance

    play_dir = unregister_instance(context.paths, arguments.instance_id)
    if not arguments.delete_worlds:
        say(f"đã gỡ {arguments.instance_id}; thế giới vẫn còn ở {play_dir}")
        return 0
    shutil.rmtree(play_dir, ignore_errors=True)
    say(f"đã gỡ {arguments.instance_id} và xoá {play_dir}")
    return 0
