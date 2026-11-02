"""Bundled service origins work without user input; invalid origins never enable Google."""

from pathlib import Path

import pytest

from nostalgia.social import configuration
from nostalgia.social.configuration import load_configuration, read_configuration


def test_user_file_wins_over_bundled_and_env_wins_over_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = tmp_path / "configuration.py"
    monkeypatch.setattr(configuration, "__file__", str(module))
    (tmp_path / "service-defaults.json").write_text(
        '{"account_url":"https://bundled.test/","room_sync_url":"https://bundled-room.test"}'
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    assert read_configuration(config_dir).account_url == "https://bundled.test"
    (config_dir / "services.json").write_text(
        '{"account_url":"https://user.test","room_sync_url":""}'
    )
    loaded = read_configuration(config_dir)
    assert loaded.account_url == "https://user.test"
    # Trường trống trong file người dùng thì lấy giá trị cài sẵn.
    assert loaded.room_sync_url == "https://bundled-room.test"
    (config_dir / "services.json").write_text("{broken")
    assert read_configuration(config_dir).account_url == "https://bundled.test"
    (config_dir / "services.json").write_text('{"account_url":"https://user.test"}')
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


def test_plus_flag_is_explicit_and_not_inferred_from_account_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(configuration, "__file__", str(tmp_path / "configuration.py"))
    monkeypatch.delenv("NOSTALGIA_PLUS_ENABLED", raising=False)
    (tmp_path / "service-defaults.json").write_text('{"account_url":"https://bundled.test"}')
    assert (
        read_configuration(tmp_path).account_url and not read_configuration(tmp_path).plus_enabled
    )
    (tmp_path / "service-defaults.json").write_text(
        '{"account_url":"https://bundled.test","plus_enabled":true}'
    )
    assert read_configuration(tmp_path).plus_enabled
    # services.json của người dùng không tự bật được bán Plus.
    (tmp_path / "services.json").write_text('{"plus_enabled":true}')
    (tmp_path / "service-defaults.json").write_text('{"plus_enabled":"yes"}')
    assert not read_configuration(tmp_path).plus_enabled
    monkeypatch.setenv("NOSTALGIA_PLUS_ENABLED", "1")
    assert read_configuration(tmp_path).plus_enabled
    (tmp_path / "service-defaults.json").write_text('{"plus_enabled":true}')
    monkeypatch.setenv("NOSTALGIA_PLUS_ENABLED", "0")
    assert not read_configuration(tmp_path).plus_enabled
