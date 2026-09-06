"""Cấu hình người dùng: ghi 0600, biến môi trường thắng file, file hỏng không chặn launcher."""

from __future__ import annotations

import stat
from pathlib import Path

from nostalgia.settings.store import Settings, load_settings, save_settings, settings_path


def test_round_trip_is_private_and_env_overrides(tmp_path: Path) -> None:
    save_settings(tmp_path, Settings(curseforge_api_key="  $2a$10$khoa  "))

    assert stat.S_IMODE(settings_path(tmp_path).stat().st_mode) == 0o600
    assert load_settings(tmp_path, environment={}).curseforge_api_key == "$2a$10$khoa"
    assert (
        load_settings(
            tmp_path, environment={"NOSTALGIA_CURSEFORGE_API_KEY": "env"}
        ).curseforge_api_key
        == "env"
    )


def test_missing_or_corrupt_file_means_empty_settings(tmp_path: Path) -> None:
    assert load_settings(tmp_path, environment={}) == Settings()
    settings_path(tmp_path).write_text("{ hỏng")
    assert not load_settings(tmp_path, environment={}).has_curseforge_key
