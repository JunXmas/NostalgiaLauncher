"""Tiến trình thoát giữa exists/open/read trên procfs phải được coi là đã dừng."""

import os
import sys
from pathlib import Path

import pytest
from test_game_process import is_alive


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs")
@pytest.mark.parametrize("error_type", [FileNotFoundError, ProcessLookupError])
def test_disappearing_proc_entry_is_an_exited_process(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[OSError],
) -> None:
    def disappeared(_path: Path, *_args: object, **_kwargs: object) -> str:
        raise error_type("Process exited before reading its status")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_text", disappeared)
        assert not is_alive(os.getpid())
