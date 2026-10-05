"""`nostalgia account` — thêm, liệt kê, xoá tài khoản offline.

Mọi thứ nặng được **nạp lười bên trong `run`** — xem `cli/commands/version.py` để biết lý do.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nostalgia.cli.context import CliContext


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("account", help="quản lý tài khoản")
    actions = parser.add_subparsers(dest="account_action", required=True)

    add_offline = actions.add_parser("add-offline", help="thêm tài khoản offline")
    add_offline.add_argument("player_name", help="tên trong game, 3-16 ký tự")
    add_offline.set_defaults(run=run_add_offline)

    add_microsoft = actions.add_parser(
        "add-microsoft", help="đăng nhập bằng tài khoản Microsoft (cần mã ứng dụng Azure)"
    )
    add_microsoft.set_defaults(run=run_add_microsoft)

    actions.add_parser("list", help="liệt kê tài khoản đã lưu").set_defaults(run=run_list)

    remove = actions.add_parser("remove", help="xoá một tài khoản")
    remove.add_argument("player_name")
    remove.set_defaults(run=run_remove)

    parser.set_defaults(run=run_list)


def run_add_offline(arguments: argparse.Namespace, context: CliContext) -> int:
    from nostalgia.account.offline import build_offline_account
    from nostalgia.account.store import load_accounts, save_accounts, upsert_account
    from nostalgia.cli.output import say

    account = build_offline_account(arguments.player_name)
    accounts = load_accounts(context.paths.accounts_json)
    save_accounts(context.paths.accounts_json, upsert_account(accounts, account))
    say(f"đã thêm {account.player_name} ({account.player_uuid})")
    return 0


def run_add_microsoft(_arguments: argparse.Namespace, context: CliContext) -> int:
    """Đăng nhập bằng device code: in mã ra rồi chờ người dùng nhập trên trang của Microsoft."""
    import os
    import time

    from nostalgia.account.microsoft import build_microsoft_account
    from nostalgia.account.store import load_accounts, save_accounts, upsert_account
    from nostalgia.auth.device_code import DeviceCode
    from nostalgia.auth.microsoft import resolve_client_id, sign_in
    from nostalgia.cli.output import say
    from nostalgia.net.http import HttpClient

    client_id = resolve_client_id(os.environ)

    def show(device_code: DeviceCode) -> None:
        say(f"Mở {device_code.verification_url} rồi nhập mã: {device_code.user_code}")
        say("Đang chờ bạn đăng nhập... (Ctrl+C để dừng)")

    with HttpClient() as http_client:
        login = sign_in(http_client, client_id, show, cancel_token=context.cancel_token)
    account = build_microsoft_account(login, now=time.time())

    accounts = load_accounts(context.paths.accounts_json)
    save_accounts(context.paths.accounts_json, upsert_account(accounts, account))
    if not login.minecraft_session.owns_game:
        say(f"đã thêm {account.player_name} — tài khoản này CHƯA MUA game, chỉ chơi được bản thử")
    else:
        say(f"đã thêm {account.player_name} ({account.player_uuid})")
    return 0


def run_list(_arguments: argparse.Namespace, context: CliContext) -> int:
    from nostalgia.account.store import load_accounts
    from nostalgia.cli.output import say

    accounts = load_accounts(context.paths.accounts_json)
    if not accounts:
        say("chưa có tài khoản nào — chạy `nostalgia account add-offline <tên>`")
        return 0
    for account in accounts:
        say(f"{account.player_name}  {account.player_uuid}  {account.account_kind}")
    return 0


def run_remove(arguments: argparse.Namespace, context: CliContext) -> int:
    from nostalgia.account.store import find_account, load_accounts, remove_account, save_accounts
    from nostalgia.cli.output import fail, say

    accounts = load_accounts(context.paths.accounts_json)
    if find_account(accounts, arguments.player_name) is None:
        fail(f"không có tài khoản {arguments.player_name!r}")
        return 1
    save_accounts(context.paths.accounts_json, remove_account(accounts, arguments.player_name))
    say(f"đã xoá {arguments.player_name}")
    return 0
