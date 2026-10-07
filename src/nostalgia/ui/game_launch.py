"""Complete installation and Nos Client injection before freezing the host's pack."""

from __future__ import annotations

from nostalgia.api import Launcher
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn


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
