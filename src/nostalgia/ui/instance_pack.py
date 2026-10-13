"""Bundled modpack status and background updates for the instance manager."""

from typing import TYPE_CHECKING

from nostalgia.api import Instance, Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.operations.cancellation import CancelToken

if TYPE_CHECKING:
    from nostalgia.ui.instance_bridge import InstanceBridge


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


def start_builtin_update(main_bridge: "InstanceBridge", instance_id: str) -> None:
    if main_bridge.busy or main_bridge.storageBusy or getattr(main_bridge, "_game_running", False):
        main_bridge.failed.emit(
            "Đóng Minecraft và đợi công việc hiện tại hoàn tất trước khi cập nhật."
        )
        return
    cancel_token = CancelToken()

    def work() -> None:
        main_bridge._launcher.update_builtin_modpack(
            instance_id, on_progress=main_bridge.report_progress, cancel_token=cancel_token
        )
        main_bridge.announce_instances_changed()

    main_bridge.run_in_background(work, "Cập nhật modpack — giữ dữ liệu và thiết lập")
