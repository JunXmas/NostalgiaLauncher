"""Chuẩn bị game và Nos Client trước khi chụp bộ mod; chọn log đúng bản chơi."""

from __future__ import annotations

from pathlib import Path

from nostalgia.api import Launcher
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn


def load_game_log_path(launcher: Launcher, instance_id: str) -> Path:
    selected = next(i for i in launcher.list_instances() if i.instance_id == instance_id)
    return launcher.instance_game_dir(selected) / "logs" / "latest.log"


def prepare_game(
    launcher: Launcher,
    instance_id: str,
    on_progress: ProgressFn,
    cancel_token: CancelToken | None,
) -> None:
    instance = next((i for i in launcher.list_instances() if i.instance_id == instance_id), None)
    if instance is not None:
        launcher.install_version(
            instance.version_id, on_progress=on_progress, cancel_token=cancel_token
        )
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        if instance.nos_client_enabled:
            launcher.prepare_nos_client(instance)
