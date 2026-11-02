"""Chuẩn bị game và Nos Client trước khi chụp bộ mod; chọn log đúng bản chơi."""

from __future__ import annotations

from pathlib import Path

from nostalgia.api import Launcher
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn
from nostalgia.storage.directory_swap import recover_directory


def load_game_dir(launcher: Launcher, instance_id: str) -> Path:
    selected = next(i for i in launcher.list_instances() if i.instance_id == instance_id)
    return launcher.instance_game_dir(selected).resolve()


def prepare_game(
    launcher: Launcher,
    instance_id: str,
    on_progress: ProgressFn,
    cancel_token: CancelToken | None,
) -> None:
    instance = next((i for i in launcher.list_instances() if i.instance_id == instance_id), None)
    if instance is not None:
        # Lần đổi phiên bản/sửa mod trước bị cắt ngang (máy tắt) thì trả bộ mod cũ về trước khi
        # game chạy và tự tạo một thư mục mods rỗng.
        game_dir = launcher.instance_game_dir(instance)
        for history in (".nostalgia-mod-versions", ".nostalgia-repairs"):
            recover_directory(game_dir / "mods", game_dir / history)
        launcher.install_version(
            instance.version_id, on_progress=on_progress, cancel_token=cancel_token
        )
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        if instance.nos_client_enabled:
            launcher.prepare_nos_client(instance)
