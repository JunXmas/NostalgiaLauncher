"""Controlled remote boundary; the real catalog, installer, disk and Java process code run."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from nostalgia.api import Launcher, ServerAccess, ServerLease
from nostalgia.errors import ServerError, SessionRevoked
from server_http_fixture import ServerHttpFixture


class ServerAccountFixture:
    def __init__(self, plan_name: str = "Pro") -> None:
        self.plan_name, self.revoked, self.paused = plan_name, False, False
        self.lease: ServerLease | None = None

    def authorize(self) -> ServerAccess:
        if self.revoked:
            raise SessionRevoked("Phiên Google đã bị thu hồi.")
        if self.paused or self.plan_name not in ("Pro", "Max", "Ultimate"):
            raise ServerError("Host server cần Pro, Max hoặc Ultimate đang hoạt động.")
        return ServerAccess(self.plan_name)

    def start(self, server_id: str) -> ServerLease:
        self.authorize()
        if self.lease:
            raise ServerError("Một server đang chạy.")
        self.lease = ServerLease(server_id, "a" * 64, int(time.time()) + 120)
        return self.lease

    def renew(self, lease: ServerLease) -> ServerLease:
        self.authorize()
        if lease != self.lease:
            raise ServerError("Phiên server không hợp lệ.")
        self.lease = replace(lease, expires_at=int(time.time()) + 120)
        return self.lease

    def release(self, lease: ServerLease) -> None:
        if self.lease == lease:
            self.lease = None


def server_launcher(tmp_path: Path) -> tuple[Launcher, ServerHttpFixture]:
    http_client = ServerHttpFixture()
    launcher = replace(
        Launcher.for_data_dir(tmp_path / "data", tmp_path / "config"),
        make_http_client=lambda: http_client,
    )
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    return launcher, http_client


def fake_java(tmp_path: Path) -> Path:
    path = tmp_path / "java-fixture"
    path.write_text(
        "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
        "print('Done (0.2s)! For help, type help',flush=True)\n"
        "for line in sys.stdin:\n"
        " Path('commands.txt').open('a').write(line)\n"
        " print(line.strip(),flush=True)\n"
        " if line.strip()=='stop':\n"
        "  Path('saved-world.txt').write_text('saved')\n"
        "  break\n"
    )
    path.chmod(0o755)
    return path
