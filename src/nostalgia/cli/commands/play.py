"""`nostalgia play` — khởi động game. Đây là đích của mốc M1.

Mọi thứ nặng được **nạp lười bên trong `run`** — xem `cli/commands/version.py` để biết lý do.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from nostalgia.account.model import Account
    from nostalgia.cli.context import CliContext
    from nostalgia.launch.command import LaunchCommand
    from nostalgia.version.meta import VersionMeta


CANCELLED_EXIT_CODE = 130

# Nhịp đợi game. Đủ ngắn để Ctrl+C có cảm giác tức thì, đủ dài để không quay vòng bận.
WAIT_TICK_SECONDS = 0.2


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("play", help="khởi động game")
    parser.add_argument("version_id", help="mã phiên bản, ví dụ 1.20.1")
    parser.add_argument("--account", required=True, help="tên tài khoản đã lưu")
    parser.add_argument("--game-dir", help="thư mục chạy game (mặc định: <data>/game/<bản>)")
    parser.add_argument("--max-memory", type=int, default=None, help="bộ nhớ tối đa, tính bằng MB")
    parser.add_argument("--width", type=int, default=None, help="chiều rộng cửa sổ")
    parser.add_argument("--height", type=int, default=None, help="chiều cao cửa sổ")
    parser.add_argument("--demo", action="store_true", help="chạy chế độ dùng thử")
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="in lệnh (đã che vé đăng nhập) rồi thoát, không chạy game",
    )
    parser.set_defaults(run=run)


def run(arguments: argparse.Namespace, context: CliContext) -> int:
    from pathlib import Path

    from nostalgia.account.model import to_player_profile
    from nostalgia.account.store import find_account, load_accounts
    from nostalgia.cli.output import fail, print_diagnosis, say
    from nostalgia.doctor import diagnose
    from nostalgia.install.assets import load_installed_asset_index
    from nostalgia.launch.command import LaunchOptions, build_launch_command
    from nostalgia.launch.runner import resolve_installed_java_binary
    from nostalgia.launch.tuning import JvmTuning
    from nostalgia.repo.version_repo import VersionRepository

    account = find_account(load_accounts(context.paths.accounts_json), arguments.account)
    if account is None:
        fail(f"không có tài khoản {arguments.account!r} — xem `nostalgia account list`")
        return 1
    account = _refresh_if_needed(account, context)

    repository = VersionRepository(context.paths)
    version_id = arguments.version_id
    if not repository.is_installed(version_id):
        fail(f"chưa cài {version_id} — chạy `nostalgia install {version_id}`")
        return 1
    version_meta = repository.load_version_meta(version_id)

    java_binary = resolve_installed_java_binary(version_meta, context.platform, context.paths)
    if java_binary is None:
        fail(f"chưa có bản Java cho {version_id} — chạy `nostalgia install {version_id}`")
        return 1

    diagnosis = diagnose(
        version_meta,
        context.platform,
        context.paths,
        asset_index=load_installed_asset_index(version_meta, context.paths),
        java_binary=java_binary,
        cancel_token=context.cancel_token,
    )
    if not diagnosis.is_healthy:
        print_diagnosis(diagnosis, version_id)
        fail(f"bản cài thiếu — chạy `nostalgia install {version_id} --repair`")
        return 1

    game_dir = (
        Path(arguments.game_dir) if arguments.game_dir else _default_game_dir(context, version_id)
    )
    command = build_launch_command(
        version_meta,
        context.platform,
        context.paths,
        to_player_profile(account),
        java_binary,
        LaunchOptions(
            game_dir=game_dir,
            window_width=arguments.width,
            window_height=arguments.height,
            is_demo=arguments.demo,
        ),
        tuning=JvmTuning(max_heap_megabytes=arguments.max_memory) if arguments.max_memory else None,
        virtual_assets_dir=_virtual_assets_dir(version_meta, context),
    )

    if arguments.print_command:
        say(" ".join(command.masked_argv()))
        return 0

    return _run_game(command, context, account.player_name, version_id)


def _run_game(
    command: LaunchCommand, context: CliContext, player_name: str, version_id: str
) -> int:
    """Chạy game và đợi. Vòng lặp có ĐÚNG HAI lối ra: game thoát, hoặc người dùng bấm dừng.

    Phải đợi theo từng nhịp ngắn thay vì đợi một lần vô hạn: Ctrl+C chỉ đặt cờ huỷ (game nằm
    ở phiên riêng nên nó không nhận được tín hiệu từ terminal), và cờ đó chỉ được nhìn thấy
    giữa hai nhịp.
    """
    import subprocess

    from nostalgia.cli.output import say
    from nostalgia.launch.game_process import start_game

    say(f"khởi động {version_id} với tài khoản {player_name}")
    game = start_game(command, on_output=_drop if context.quiet else say)
    while not context.cancel_token.is_cancelled():
        try:
            return game.wait(timeout=WAIT_TICK_SECONDS)
        except subprocess.TimeoutExpired:
            continue
    say("đang dừng game...")
    game.stop()
    return CANCELLED_EXIT_CODE


def _refresh_if_needed(account: Account, context: CliContext) -> Account:
    """Làm mới vé Microsoft trước khi chạy, và phân biệt hai kiểu hỏng.

    - Vé làm mới đã chết (`AuthError`): dứt khoát, phải đăng nhập lại. Để nguyên vé cũ mà
      chạy chỉ đẩy lỗi sang cho Minecraft báo bằng thông báo khó hiểu hơn nhiều.
    - Không có mạng (`NetworkError`): chưa chắc vé đã hỏng. Cảnh báo rồi chạy tiếp bằng vé
      đang có — chơi một mình thì thường vẫn vào được.
    """
    import os
    import time

    from nostalgia.account.microsoft import needs_refresh, refresh_account
    from nostalgia.account.store import load_accounts, save_accounts, upsert_account
    from nostalgia.auth.microsoft import resolve_client_id
    from nostalgia.cli.output import say, warn
    from nostalgia.errors import NetworkError
    from nostalgia.net.http import HttpClient

    if not needs_refresh(account, now=time.time()):
        return account

    say(f"vé của {account.player_name} đã cũ, đang làm mới...")
    try:
        with HttpClient() as http_client:
            refreshed = refresh_account(
                http_client,
                resolve_client_id(os.environ),
                account,
                now=time.time(),
                cancel_token=context.cancel_token,
            )
    except NetworkError as error:
        warn(f"không làm mới được vé ({error}); thử chạy bằng vé đang có")
        return account

    accounts = load_accounts(context.paths.accounts_json)
    save_accounts(context.paths.accounts_json, upsert_account(accounts, refreshed))
    return refreshed


def _drop(_line: str) -> None:
    """Chế độ im lặng: vẫn phải đọc ống, nếu không game sẽ nghẽn khi bộ đệm đầy."""


def _default_game_dir(context: CliContext, version_id: str) -> Path:
    """Mỗi phiên bản một thư mục chạy riêng: trộn chung là bản mới ăn thế giới của bản cũ."""
    return context.paths.data_dir / "game" / version_id


def _virtual_assets_dir(version_meta: VersionMeta, context: CliContext) -> Path | None:
    """Đời ≤1.7 đọc asset theo TÊN, nên `--assetsDir` phải trỏ vào cây tên."""
    from nostalgia.install.assets import load_installed_asset_index

    asset_index = load_installed_asset_index(version_meta, context.paths)
    if asset_index is None or not asset_index.is_virtual or not version_meta.assets_id:
        return None
    return context.paths.virtual_assets_dir(version_meta.assets_id)
