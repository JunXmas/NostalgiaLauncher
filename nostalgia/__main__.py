"""CLI: đăng nhập, cài phiên bản, chạy game.

Tài khoản đã mua game -> chạy full game.
Tài khoản Microsoft chưa mua -> tự động chạy demo mode chính thức.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import accounts, auth
from .install import Installer
from .launch import build_command, ensure_offline_libraries, run

from .paths import APP_NAME, DEFAULT_GAME_DIR, migrate_legacy


def client_id() -> str:
    from .settings import client_id as resolve
    cid = resolve("microsoft", "MC_CLIENT_ID")
    if not cid:
        sys.exit(
            "Thiếu MC_CLIENT_ID.\n"
            "Đăng ký app tại https://portal.azure.com > App registrations:\n"
            "  - Supported account types: Personal Microsoft accounts only\n"
            "  - Authentication > Allow public client flows: Yes\n"
            "Rồi: export MC_CLIENT_ID=<application-id>\n"
            "hoặc lưu vào ~/.config/nostalgia-launcher/clients.json"
        )
    return cid


def cmd_account_add(args) -> None:
    """Thêm một tài khoản Microsoft. Mỗi người chơi đăng nhập tài khoản của mình."""
    cid = client_id()
    store = accounts.AccountStore()

    flow = auth.request_device_code(cid)
    print(f"\n  Mở {flow['verification_uri']} và nhập mã: {flow['user_code']}\n")
    tokens = auth.poll_for_token(cid, flow["device_code"], flow["interval"], flow["expires_in"])
    session = auth.complete_login(tokens)

    label = args.label or store.unique_label(session.username if session.owns_game else "demo")
    account = accounts.StoredAccount.from_session(session, label)
    if not session.owns_game:
        account.demo_name = args.name or label
    store.upsert(account)

    if session.owns_game:
        print(f"Đã thêm '{label}': có bản quyền, chơi full game.")
    else:
        print(
            f"Đã thêm '{label}': tài khoản hợp lệ nhưng chưa mua game.\n"
            f"Sẽ chạy demo mode chính thức với tên hiển thị '{account.demo_name}'."
        )
    print(f"Tài khoản mặc định hiện tại: {store.default_label}")


def cmd_account_add_offline(args) -> None:
    """Thêm hồ sơ offline. Chỉ mở khi launcher đã có tài khoản sở hữu game."""
    store = accounts.AccountStore()
    try:
        account = store.add_offline(args.name, args.label)
    except accounts.OwnershipRequired as e:
        sys.exit(f"{e}\nThêm bằng: python -m nostalgia account add")
    print(f"Đã thêm hồ sơ offline '{account.label}' (tên trong game: {account.username}).")


def _mode_of(store: accounts.AccountStore, a: accounts.StoredAccount) -> str:
    if a.kind == accounts.OFFLINE:
        return "offline" if store.any_owns_game() else "offline->demo"
    return "full game" if a.owns_game else "demo"


def cmd_account_list(args) -> None:
    store = accounts.AccountStore()
    if not store.accounts:
        print("Chưa có tài khoản nào. Chạy: python -m nostalgia account add")
        return
    print(f"  {'':2s} {'LABEL':20s} {'LOẠI':9s} {'CHẾ ĐỘ':14s} TÊN TRONG GAME")
    for a in store.accounts:
        marker = "*" if a.label == store.default_label else " "
        name = a.username if (a.owns_game or a.kind == accounts.OFFLINE) else a.demo_name
        print(f"  {marker:2s} {a.label:20s} {a.kind:9s} {_mode_of(store, a):14s} {name}")
    print("\n  * = mặc định khi chạy `play` không kèm --account")
    if not store.any_owns_game():
        print("  Chưa có tài khoản nào sở hữu game: hồ sơ offline sẽ chạy ở demo mode.")


def cmd_account_remove(args) -> None:
    store = accounts.AccountStore()
    if store.remove(args.label):
        print(f"Đã xoá '{args.label}'. Mặc định hiện tại: {store.default_label}")
    else:
        sys.exit(f"Không có tài khoản nào tên '{args.label}'.")


def cmd_account_default(args) -> None:
    store = accounts.AccountStore()
    if store.set_default(args.label):
        print(f"Tài khoản mặc định: {args.label}")
    else:
        sys.exit(f"Không có tài khoản nào tên '{args.label}'.")


def cmd_gui(args) -> None:
    try:
        from .ui.app import run_gui
    except ImportError:
        sys.exit("Cần PySide6: pip install PySide6-Essentials")
    # Chỉ ghi đè cấu hình đã lưu khi người dùng nêu rõ trên dòng lệnh.
    override = args.game_dir if args.game_dir != DEFAULT_GAME_DIR else None
    sys.exit(run_gui(override, args.version))


def cmd_doctor(args) -> None:
    from .doctor import diagnose
    from .settings import Settings
    cfg = Settings.load()
    report = diagnose(Installer(args.game_dir), args.version,
                      memory_mb=cfg.memory_mb, java_path=cfg.java_path,
                      verify_hashes=args.hashes)
    print(report.text(show_command=args.command))
    sys.exit(1 if report.failed else 0)


def cmd_fabric(args) -> None:
    from . import fabric
    installer = Installer(args.game_dir)
    if args.list:
        for v in fabric.list_game_versions()[: args.limit]:
            print(f"  {v}")
        return
    version_id = fabric.install(installer, args.version, args.loader)
    print(f"Đã cài {version_id}. Chạy: python -m nostalgia play {version_id}")


def cmd_versions(args) -> None:
    for v in Installer(args.game_dir).list_versions(args.type)[: args.limit]:
        print(f"  {v}")


def cmd_install(args) -> None:
    Installer(args.game_dir).install(args.version)


def cmd_play(args) -> None:
    store = accounts.AccountStore()
    if not store.accounts:
        sys.exit("Chưa có tài khoản. Chạy: python -m nostalgia account add")
    account = store.get(args.account)
    if account is None:
        sys.exit(f"Không có tài khoản nào tên '{args.account}'. Xem: account list")

    if account.kind == accounts.MSA:
        account = accounts.refresh_if_online(store, account, client_id())
    identity = store.resolve_identity(account, override_name=args.name)

    if account.kind == accounts.OFFLINE and identity.demo:
        print("  [cảnh báo] Không còn tài khoản nào sở hữu game -> hạ xuống demo mode.")

    installer = Installer(args.game_dir)
    meta = installer.install(args.version)
    if identity.user_type == accounts.OFFLINE:
        ensure_offline_libraries(meta, installer)
    cmd = build_command(meta, installer, identity, max_memory_mb=args.memory)

    mode = "DEMO" if identity.demo else "full"
    print(f"\nKhởi động {args.version} [{mode}] với tài khoản '{account.label}'...\n")
    sys.exit(run(cmd, args.game_dir))


def main() -> None:
    migrate_legacy()
    parser = argparse.ArgumentParser(prog="nostalgia", description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    sub = parser.add_subparsers(dest="cmd", required=True)

    acc = sub.add_parser("account", help="quản lý tài khoản").add_subparsers(
        dest="account_cmd", required=True
    )

    p = acc.add_parser("add", help="thêm một tài khoản Microsoft")
    p.add_argument("--label", help="tên gợi nhớ; mặc định lấy tên tài khoản")
    p.add_argument("--name", help="tên hiển thị trong game (chỉ dùng cho tài khoản demo)")
    p.set_defaults(func=cmd_account_add)

    p = acc.add_parser("add-offline", help="thêm hồ sơ offline (cần đã có tài khoản sở hữu game)")
    p.add_argument("name", help="tên trong game")
    p.add_argument("--label", help="tên gợi nhớ; mặc định lấy theo name")
    p.set_defaults(func=cmd_account_add_offline)

    p = acc.add_parser("list", help="liệt kê tài khoản đã lưu")
    p.set_defaults(func=cmd_account_list)

    p = acc.add_parser("remove", help="xoá một tài khoản")
    p.add_argument("label")
    p.set_defaults(func=cmd_account_remove)

    p = acc.add_parser("default", help="đặt tài khoản mặc định")
    p.add_argument("label")
    p.set_defaults(func=cmd_account_default)

    p = sub.add_parser("gui", help="mở giao diện đồ hoạ")
    p.add_argument("--version", default="", help="ghi đè phiên bản đang chọn")
    p.set_defaults(func=cmd_gui)

    p = sub.add_parser("doctor", help="soi từng mắt xích của một bản cài đặt")
    p.add_argument("version")
    p.add_argument("--hashes", action="store_true", help="kiểm SHA1 mọi thư viện (chậm)")
    p.add_argument("--command", action="store_true", help="in cả lệnh sẽ chạy")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("fabric", help="cài Fabric loader cho một phiên bản")
    p.add_argument("version", nargs="?", default="", help="phiên bản game, ví dụ 1.21.4")
    p.add_argument("--loader", help="phiên bản loader; mặc định lấy bản mới nhất")
    p.add_argument("--list", action="store_true", help="liệt kê phiên bản Fabric hỗ trợ")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_fabric)

    p = sub.add_parser("versions", help="liệt kê phiên bản")
    p.add_argument("--type", default="release", choices=["release", "snapshot", "all"])
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_versions)

    p = sub.add_parser("install", help="tải một phiên bản")
    p.add_argument("version")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("play", help="cài (nếu cần) và chạy game")
    p.add_argument("version")
    p.add_argument("--account", help="label tài khoản; mặc định lấy cái đầu tiên")
    p.add_argument("--name", help="ghi đè tên hiển thị demo cho lần chạy này")
    p.add_argument("--memory", type=int, default=2048, help="RAM tối đa (MB)")
    p.set_defaults(func=cmd_play)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
