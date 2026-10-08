"""Keep disabled mod copies when the same filename is replaced again."""

import uuid
from pathlib import Path

from nostalgia.errors import ContentError
from nostalgia.storage.files import resolve_child


def disable_archive(destination: Path) -> None:
    disabled = resolve_child(destination.parent, destination.name + ".disabled")
    if disabled.exists():
        disabled = resolve_child(
            destination.parent, destination.name + "." + uuid.uuid4().hex + ".disabled"
        )
    if disabled.exists():
        raise ContentError("Bản mod tắt đã tồn tại; không ghi đè.")
    destination.rename(disabled)
