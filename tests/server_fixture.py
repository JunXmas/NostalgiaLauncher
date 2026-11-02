"""Controlled remote boundary; the real catalog, installer, disk and Java process code run."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from nostalgia.api import Launcher
from server_http_fixture import ServerHttpFixture


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
