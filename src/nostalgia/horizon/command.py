"""Lệnh native: tài khoản offline chỉ truyền tên; phiên Microsoft đi qua stdin."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from nostalgia.account.model import ELY, MICROSOFT, OFFLINE, Account
from nostalgia.errors import InstanceError
from nostalgia.horizon.model import HorizonBuild
from nostalgia.launch.command import LaunchOptions
from nostalgia.skin.model import PlayerSkin


@dataclass(frozen=True, slots=True)
class HorizonCommand:
    argv: tuple[str, ...]
    game_dir: Path
    standard_input: bytes = field(default=b"", repr=False)
    secret_values: frozenset[str] = field(default_factory=frozenset, repr=False)
    player_skin: PlayerSkin | None = None


def build_horizon_command(
    build: HorizonBuild,
    account: Account,
    options: LaunchOptions,
    player_skin: PlayerSkin | None = None,
) -> HorizonCommand:
    if re.fullmatch(r"[A-Za-z0-9_]{3,16}", account.player_name) is None:
        raise InstanceError("Horizon needs a player name of 3-16 letters, digits or underscores")
    argv = [
        str(build.game_binary),
        "--resources",
        str(build.resources_dir),
        "--game-dir",
        str(options.game_dir),
        "--home",
        str(options.game_dir),
    ]
    standard_input = b""
    secrets: frozenset[str] = frozenset()
    if account.account_kind == MICROSOFT:
        if not account.access_token:
            raise InstanceError("Sign in to the Microsoft account again before playing Horizon")
        argv.append("--session-stdin")
        standard_input = json.dumps(
            {
                "name": account.player_name,
                "uuid": account.player_uuid,
                "access_token": account.access_token,
                "user_type": "msa",
            }
        ).encode("utf-8")
        secrets = frozenset({account.access_token})
    elif account.account_kind in (OFFLINE, ELY):
        # --name có trong CLI native 0.1; không gán user_type msa hoặc vé giả cho offline.
        argv.extend(("--name", account.player_name))
    else:
        raise InstanceError("Unsupported Horizon account kind")
    for flag, value in (("--width", options.window_width), ("--height", options.window_height)):
        if value is not None:
            argv.extend((flag, str(value)))
    if options.world_folder:
        argv.extend(("--quickPlaySingleplayer", options.world_folder))
    if options.server_address:
        argv.extend(("--quickPlayMultiplayer", options.server_address))
    return HorizonCommand(tuple(argv), options.game_dir, standard_input, secrets, player_skin)
