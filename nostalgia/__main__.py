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
            "MC_CLIENT_ID is not set.\n"
            "Register an app at https://portal.azure.com > App registrations:\n"
            "  - Supported account types: Personal Microsoft accounts only\n"
            "  - Authentication > Allow public client flows: Yes\n"
            "Then: export MC_CLIENT_ID=<application-id>\n"
            "or save it to ~/.config/nostalgia-launcher/clients.json"
        )
    return cid


def cmd_account_add(args) -> None:
    """Add a Microsoft account. Each player signs in with their own."""
    cid = client_id()
    store = accounts.AccountStore()

    flow = auth.request_device_code(cid)
    print(f"\n  Open {flow['verification_uri']} and enter the code: {flow['user_code']}\n")
    tokens = auth.poll_for_token(cid, flow["device_code"], flow["interval"], flow["expires_in"])
    session = auth.complete_login(tokens)

    label = args.label or store.unique_label(session.username if session.owns_game else "demo")
    account = accounts.StoredAccount.from_session(session, label)
    if not session.owns_game:
        account.demo_name = args.name or label
    store.upsert(account)

    if session.owns_game:
        print(f"Added '{label}': owns the game, full game.")
    else:
        print(
            f"Added '{label}': valid account but does not own the game.\n"
            f"Will run official demo mode with display name '{account.demo_name}'."
        )
    print(f"Current default account: {store.default_label}")


def cmd_account_add_offline(args) -> None:
    """Add an offline profile. Only available once a game-owning account exists."""
    store = accounts.AccountStore()
    try:
        account = store.add_offline(args.name, args.label)
    except accounts.OwnershipRequired as e:
        sys.exit(f"{e}\nAdd one with: python -m nostalgia account add")
    print(f"Added offline profile '{account.label}' (in-game name: {account.username}).")


def _mode_of(store: accounts.AccountStore, a: accounts.StoredAccount) -> str:
    if a.kind == accounts.OFFLINE:
        return "offline" if store.any_owns_game() else "offline->demo"
    return "full game" if a.owns_game else "demo"


def cmd_account_list(args) -> None:
    store = accounts.AccountStore()
    if not store.accounts:
        print("No accounts yet. Run: python -m nostalgia account add")
        return
    print(f"  {'':2s} {'LABEL':20s} {'TYPE':9s} {'MODE':14s} IN-GAME NAME")
    for a in store.accounts:
        marker = "*" if a.label == store.default_label else " "
        name = a.username if (a.owns_game or a.kind == accounts.OFFLINE) else a.demo_name
        print(f"  {marker:2s} {a.label:20s} {a.kind:9s} {_mode_of(store, a):14s} {name}")
    print("\n  * = default when running `play` without --account")
    if not store.any_owns_game():
        print("  No game-owning account: offline profiles will run in demo mode.")


def cmd_account_remove(args) -> None:
    store = accounts.AccountStore()
    if store.remove(args.label):
        print(f"Removed '{args.label}'. Current default: {store.default_label}")
    else:
        sys.exit(f"No account named '{args.label}'.")


def cmd_account_default(args) -> None:
    store = accounts.AccountStore()
    if store.set_default(args.label):
        print(f"Default account: {args.label}")
    else:
        sys.exit(f"No account named '{args.label}'.")


def cmd_gui(args) -> None:
    try:
        from .ui.app import run_gui
    except ImportError:
        sys.exit("PySide6 required: pip install PySide6-Essentials")
    # Chỉ ghi đè cấu hình đã lưu khi người dùng nêu rõ trên dòng lệnh.
    override = args.game_dir if args.game_dir != DEFAULT_GAME_DIR else None
    sys.exit(run_gui(override, args.version))


def cmd_jre(args) -> None:
    from . import jre
    installer = Installer(args.game_dir)
    meta = installer.version_json(args.version)
    comp = jre.component_of(meta)
    if jre.is_installed(args.game_dir, comp) and not args.force:
        print(f"JRE '{comp}' already at {jre.java_binary(args.game_dir, comp)}")
        return
    def on(stage, done, total):
        if done == total or done % 40 == 0:
            print(f"  {stage}: {done}/{total}")
    binp = jre.install(args.game_dir, comp, on_progress=on)
    print(f"Done. Java at: {binp}")


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
    print(f"Installed {version_id}. Run: python -m nostalgia play {version_id}")


def cmd_versions(args) -> None:
    for v in Installer(args.game_dir).list_versions(args.type)[: args.limit]:
        print(f"  {v}")


def cmd_install(args) -> None:
    Installer(args.game_dir).install(args.version)


def cmd_play(args) -> None:
    store = accounts.AccountStore()
    if not store.accounts:
        sys.exit("No accounts. Run: python -m nostalgia account add")
    account = store.get(args.account)
    if account is None:
        sys.exit(f"No account named '{args.account}'. See: account list")

    if account.kind == accounts.MSA:
        account = accounts.refresh_if_online(store, account, client_id())
    identity = store.resolve_identity(account, override_name=args.name)

    if account.kind == accounts.OFFLINE and identity.demo:
        print("  [warning] No game-owning account left -> dropping to demo mode.")

    installer = Installer(args.game_dir)
    meta = installer.install(args.version)
    if identity.user_type == accounts.OFFLINE:
        ensure_offline_libraries(meta, installer)
    cmd = build_command(meta, installer, identity, max_memory_mb=args.memory)

    mode = "DEMO" if identity.demo else "full"
    print(f"\nLaunching {args.version} [{mode}] with account '{account.label}'...\n")
    sys.exit(run(cmd, args.game_dir))


def main() -> None:
    migrate_legacy()
    parser = argparse.ArgumentParser(prog="nostalgia", description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    sub = parser.add_subparsers(dest="cmd", required=True)

    acc = sub.add_parser("account", help="manage accounts").add_subparsers(
        dest="account_cmd", required=True
    )

    p = acc.add_parser("add", help="add a Microsoft account")
    p.add_argument("--label", help="friendly label; defaults to the account name")
    p.add_argument("--name", help="in-game display name (demo accounts only)")
    p.set_defaults(func=cmd_account_add)

    p = acc.add_parser("add-offline", help="add an offline profile (needs a game-owning account)")
    p.add_argument("name", help="in-game name")
    p.add_argument("--label", help="friendly label; defaults to name")
    p.set_defaults(func=cmd_account_add_offline)

    p = acc.add_parser("list", help="list saved accounts")
    p.set_defaults(func=cmd_account_list)

    p = acc.add_parser("remove", help="remove an account")
    p.add_argument("label")
    p.set_defaults(func=cmd_account_remove)

    p = acc.add_parser("default", help="set the default account")
    p.add_argument("label")
    p.set_defaults(func=cmd_account_default)

    p = sub.add_parser("gui", help="open the graphical interface")
    p.add_argument("--version", default="", help="override the selected version")
    p.set_defaults(func=cmd_gui)

    p = sub.add_parser("jre", help="pre-download the JRE for a version (no manual Java)")
    p.add_argument("version")
    p.add_argument("--force", action="store_true", help="re-download even if present")
    p.set_defaults(func=cmd_jre)

    p = sub.add_parser("doctor", help="inspect every link of an installation")
    p.add_argument("version")
    p.add_argument("--hashes", action="store_true", help="verify SHA1 of every library (slow)")
    p.add_argument("--command", action="store_true", help="also print the launch command")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("fabric", help="install the Fabric loader for a version")
    p.add_argument("version", nargs="?", default="", help="game version, e.g. 1.21.4")
    p.add_argument("--loader", help="loader version; defaults to the latest")
    p.add_argument("--list", action="store_true", help="list Fabric-supported versions")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_fabric)

    p = sub.add_parser("versions", help="list versions")
    p.add_argument("--type", default="release", choices=["release", "snapshot", "all"])
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_versions)

    p = sub.add_parser("install", help="download a version")
    p.add_argument("version")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("play", help="install (if needed) and launch the game")
    p.add_argument("version")
    p.add_argument("--account", help="account label; defaults to the first one")
    p.add_argument("--name", help="override the demo display name for this run")
    p.add_argument("--memory", type=int, default=2048, help="max RAM (MB)")
    p.set_defaults(func=cmd_play)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
