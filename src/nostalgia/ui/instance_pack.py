"""Bundled modpack status and background updates for the instance manager."""

from collections.abc import Callable

from nostalgia.api import Instance, Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn


def builtin_pack_row(launcher: Launcher, instance: Instance) -> dict[str, object]:
    try:
        pack_status = launcher.builtin_pack_status(instance)
    except NostalgiaError:
        pack_status = None
    return {
        "modpackPreset": "forgotten-worlds" if pack_status else "",
        "modpackVersion": pack_status.installed_version if pack_status else "",
        "modpackLatestVersion": pack_status.available_version if pack_status else "",
        "modpackUpdateAvailable": pack_status.update_available if pack_status else False,
    }


def start_builtin_update(
    launcher: Launcher,
    instance_id: str,
    *,
    on_progress: ProgressFn,
    on_complete: Callable[[], None],
    run_in_background: Callable[[Callable[[], None], str], None],
) -> None:
    cancel_token = CancelToken()

    def work() -> None:
        launcher.update_builtin_modpack(
            instance_id, on_progress=on_progress, cancel_token=cancel_token
        )
        on_complete()

    run_in_background(work, "Cập nhật modpack — giữ dữ liệu và thiết lập")
