"""Mô tả tài khoản cho QML: chỉ báo có phiên web, không đưa vé xác thực ra giao diện."""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl

from nostalgia.account.model import ELY, MICROSOFT, Account
from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError

KIND_LABELS = {MICROSOFT: "MICROSOFT", ELY: "ELY.BY", "offline": "NGOẠI TUYẾN"}


def describe_account(launcher: Launcher, account: Account) -> dict[str, Any]:
    try:
        skin = launcher.describe_skin(account)
    except NostalgiaError:
        return {
            "accountId": account.account_id,
            "playerName": account.player_name,
            "accountKind": account.account_kind,
            "elyWebReady": bool(account.refresh_token) if account.account_kind == ELY else False,
            "skinFile": "",
            "capeFile": "",
        }
    return {
        "accountId": account.account_id,
        "playerName": account.player_name,
        "playerUuid": account.player_uuid,
        "accountKind": account.account_kind,
        "elyWebReady": bool(account.refresh_token) if account.account_kind == ELY else False,
        "kindLabel": KIND_LABELS.get(account.account_kind, account.account_kind.upper()),
        "skinFile": file_url(skin.skin_path),
        "skinDigest": launcher.skin_digest(skin),
        "capeFile": file_url(skin.cape_path),
        "capeDigest": launcher.cape_digest(skin),
        "slim": skin.slim,
        "isDefaultSkin": skin.is_default,
    }


def file_url(path: Path | None) -> str:
    return QUrl.fromLocalFile(str(path)).toString() if path is not None else ""
