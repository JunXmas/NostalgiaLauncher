"""Lỗi giữa lúc chép không được xóa hoặc làm cụt bản jar đang dùng."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

import pytest

from nostalgia.nos_client.installation import inject_mod


@pytest.mark.parametrize("same_name", [True, False])
def test_interrupted_copy_preserves_installed_jar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    same_name: bool,
) -> None:
    game_dir = tmp_path / "game"
    mods = game_dir / "mods"
    mods.mkdir(parents=True)
    previous = mods / "nos-client-0.4.2.jar"
    previous.write_bytes(b"known good")
    incoming = tmp_path / (previous.name if same_name else "nos-client-0.4.3.jar")
    incoming.write_bytes(b"new jar")

    def fail_copy(_source: BinaryIO, destination: BinaryIO) -> None:
        destination.write(b"partial")
        raise OSError("Simulated disk failure")

    monkeypatch.setattr(shutil, "copyfileobj", fail_copy)
    with pytest.raises(OSError, match="Simulated disk failure"):
        inject_mod(incoming, game_dir)
    assert previous.read_bytes() == b"known good"
    assert list(mods.iterdir()) == [previous]
