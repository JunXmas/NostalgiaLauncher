"""Cài mới, nâng cấp và mẫu payload không phát sinh đồng ý ngầm."""

import json
from pathlib import Path

import pytest

from nostalgia import __version__
from nostalgia.api import Launcher
from nostalgia.settings.store import Settings, load_settings, save_settings
from nostalgia.usage.configuration import load_usage_configuration


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"analytics": True},
        {"telemetry": True},
        {"discord_presence": True},
        {"usage_choice_v1": True},
        {"usage_choice_v1": "yes"},
    ],
)
def test_install_or_upgrade_never_infers_consent(tmp_path: Path, fields: dict[str, object]) -> None:
    (tmp_path / "settings.json").write_text(json.dumps(fields))
    assert load_settings(tmp_path).usage_choice_v1 == "unselected"


@pytest.mark.parametrize("choice", ["accepted", "declined"])
def test_explicit_choice_survives_restart(tmp_path: Path, choice: str) -> None:
    save_settings(tmp_path, Settings(usage_choice_v1=choice))
    assert load_settings(tmp_path).usage_choice_v1 == choice


def test_sample_is_local_illustrative_and_has_exact_contract(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    sample = json.loads(launcher.usage_payload_sample())
    assert sample == {
        "schema_version": 1,
        "event": "installation_active",
        "day": "2026-11-05",
        "launcher_version": __version__,
        "os_group": "windows",
        "daily_id": "0123456789abcdef" * 2,
    }
    assert not (launcher.paths.config_dir / "usage-day.json").exists()


def test_no_endpoint_or_readiness_disables_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOSTALGIA_USAGE_ENDPOINT", "")
    monkeypatch.setenv("NOSTALGIA_USAGE_READY", "1")
    assert not load_usage_configuration().ready
    monkeypatch.setenv("NOSTALGIA_USAGE_ENDPOINT", "https://usage.test/v1/usage")
    monkeypatch.setenv("NOSTALGIA_USAGE_READY", "0")
    assert not load_usage_configuration().ready
    monkeypatch.setenv("NOSTALGIA_USAGE_READY", "1")
    assert load_usage_configuration().ready


def test_bundled_service_readiness_does_not_supply_consent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("NOSTALGIA_USAGE_ENDPOINT", raising=False)
    monkeypatch.delenv("NOSTALGIA_USAGE_READY", raising=False)
    configuration = load_usage_configuration()
    assert configuration.ready
    assert configuration.endpoint == "https://nostalgia-payment-admin.junbob.workers.dev/v1/usage"
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    assert launcher.load_settings().usage_choice_v1 == "unselected"
    collector = launcher.usage_collector()
    collector.resume()
    assert collector.new_attempt() is None
    assert not (launcher.paths.config_dir / "usage-day.json").exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://usage.test/v1/usage",
        "https://usage.test/wrong",
        "https://user:secret@usage.test/v1/usage",
        "https://usage.test/v1/usage?account=x",
    ],
)
def test_invalid_endpoint_fails_closed(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    monkeypatch.setenv("NOSTALGIA_USAGE_ENDPOINT", url)
    monkeypatch.setenv("NOSTALGIA_USAGE_READY", "1")
    assert not load_usage_configuration().ready
