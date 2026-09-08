"""Kho tài khoản chỉ đọc đĩa khi có thay đổi.

Đo trước khi sửa: một cú bấm chọn tài khoản kéo theo 11 lần đọc + parse accounts.json, thêm
tài khoản 26 lần — vì mỗi binding QML đọc `accounts`/`activePlayerName` là một lần đọc đĩa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until

from nostalgia.account.model import Account
from nostalgia.api import Launcher
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.bridge import LauncherBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_reading_accounts_many_times_touches_the_disk_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    launcher.add_offline_account("Jun")
    launcher.add_offline_account("Notch")
    reads: list[int] = []
    original = Launcher.list_accounts

    def counted(self: Launcher) -> tuple[Account, ...]:
        reads.append(1)
        return original(self)

    monkeypatch.setattr(Launcher, "list_accounts", counted)
    main_bridge = LauncherBridge(launcher)
    account_bridge = AccountBridge(launcher, main_bridge)

    for _ in range(20):
        assert len(main_bridge.accounts) == 2
        assert main_bridge.activePlayerName == "Jun"
        assert account_bridge.accountNamed("Notch")["playerName"] == "Notch"
    main_bridge.setActiveAccount("Notch")
    assert main_bridge.activePlayerName == "Notch"
    assert len(reads) == 1, "đổi tài khoản đang chọn không phải là lý do để đọc lại đĩa"

    main_bridge.addOfflineAccount("Dinnerbone")
    wait_until(lambda: len(main_bridge.accounts) == 3 and not main_bridge.busy)
    # Lõi đọc một lần để ghi (đọc-sửa-ghi), cầu nối nạp lại một lần: không hơn.
    assert len(reads) == 3, "thêm tài khoản: cầu nối chỉ nạp lại đúng một lần"
    wait_until(lambda: account_bridge.accountNamed("Dinnerbone") != {})
    assert account_bridge.busy is False, "tài khoản ngoại tuyến không có skin để tải"
