"""Bundled service origins work without user input; invalid origins never enable Google."""

from pathlib import Path

import pytest

from nostalgia.social import configuration
from nostalgia.social.configuration import load_configuration, read_configuration


def test_bundled_origin_wins_over_old_user_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = tmp_path / "configuration.py"
    monkeypatch.setattr(configuration, "__file__", str(module))
    (tmp_path / "service-defaults.json").write_text(
        '{"account_url":"https://accounts.nostalgia.test/","room_sync_url":""}'
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "services.json").write_text('{"account_url":"https://old.test"}')
    assert read_configuration(config_dir).account_url == "https://accounts.nostalgia.test"
    (config_dir / "services.json").write_text("{broken")
    assert read_configuration(config_dir).account_url == "https://accounts.nostalgia.test"
    monkeypatch.setenv("NOSTALGIA_ACCOUNT_URL", "https://developer.test")
    assert read_configuration(config_dir).account_url == "https://developer.test"


@pytest.mark.parametrize(
    "origin",
    ["http://insecure.test", "https://user:secret@accounts.test", "https://accounts.test/callback"],
)
def test_invalid_bundled_origin_disables_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setattr(configuration, "__file__", str(tmp_path / "configuration.py"))
    (tmp_path / "service-defaults.json").write_text('{"account_url":"' + origin + '"}')
    assert not load_configuration(tmp_path).account_url
