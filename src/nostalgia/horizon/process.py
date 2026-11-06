"""Chạy native trong phiên riêng, giữ token khỏi argv và nhật ký launcher."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass

from nostalgia.errors import InstanceError
from nostalgia.horizon.command import HorizonCommand
from nostalgia.horizon.environment import build_horizon_environment
from nostalgia.launch.game_process import GameProcess, OutputFn, ignore_output
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress
from nostalgia.storage.files import ensure_dir
from nostalgia.system.platform_info import resolve_creation_flags


@dataclass(frozen=True, slots=True)
class HorizonTaskReport:
    exit_code: int
    tail: tuple[str, ...]


def start_horizon(command: HorizonCommand, *, on_output: OutputFn = ignore_output) -> GameProcess:
    ensure_dir(command.game_dir)
    environment = build_horizon_environment(command.game_dir)
    if command.player_skin is not None:
        environment["HORIZON_OFFLINE_SKIN"] = str(command.player_skin.skin_path)
        environment["HORIZON_OFFLINE_SKIN_MODEL"] = (
            "slim" if command.player_skin.slim else "classic"
        )
        if command.player_skin.cape_path is not None:
            environment["HORIZON_OFFLINE_CAPE"] = str(command.player_skin.cape_path)
    process = subprocess.Popen(
        command.argv,
        cwd=command.game_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE if command.standard_input else subprocess.DEVNULL,
        env=environment,
        start_new_session=sys.platform != "win32",
        creationflags=resolve_creation_flags(sys.platform),
    )

    def receive(line: str) -> None:
        for secret in command.secret_values:
            line = line.replace(secret, "***")
        on_output(line)

    game_process = GameProcess(process, receive)
    if command.standard_input:

        def write_session() -> None:
            if process.stdin is not None:
                try:
                    with process.stdin:
                        process.stdin.write(command.standard_input)
                except (BrokenPipeError, OSError):
                    pass

        threading.Thread(target=write_session, daemon=True).start()
    return game_process


def run_horizon_task(
    command: HorizonCommand,
    *,
    cancel_token: CancelToken | None = None,
    on_progress: ProgressFn = ignore_progress,
    timeout_seconds: float = 1800,
) -> HorizonTaskReport:
    """Chuẩn bị tài nguyên có hạn chờ, hủy được và không giữ toàn bộ output trong RAM."""
    import json

    tail: deque[str] = deque(maxlen=8)

    def receive(line: str) -> None:
        tail.append(line[:1000])
        try:
            fields = json.loads(line)
            if isinstance(fields, dict):
                fraction = fields.get("fraction")
                done = (
                    int(max(0, min(1, fraction)) * 1000)
                    if isinstance(fraction, (int, float))
                    else 0
                )
                on_progress(Progress("Preparing Horizon resources", done, 1000))
        except (ValueError, TypeError, OverflowError):
            pass

    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    game_process = start_horizon(command, on_output=receive)
    deadline = time.monotonic() + timeout_seconds
    try:
        while game_process.is_running:
            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            if time.monotonic() >= deadline:
                raise InstanceError("Horizon preparation timed out; try again")
            time.sleep(0.1)
        return HorizonTaskReport(game_process.wait(), tuple(tail))
    finally:
        if game_process.is_running:
            game_process.stop()
