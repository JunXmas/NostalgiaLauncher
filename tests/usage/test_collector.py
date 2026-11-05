"""Kiểm request thật tại biên transport, quyền cuối cùng và mã ngày độc lập định danh."""

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from nostalgia.errors import NetworkError
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.settings.store import Settings, load_settings, save_settings
from nostalgia.usage.collector import UsageCollector
from nostalgia.usage.configuration import UsageConfiguration


@dataclass(frozen=True, slots=True)
class Collection:
    collector: UsageCollector
    requests: list[tuple[str, str, dict[str, Any]]]
    config_dir: Path


@pytest.fixture
def collection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Collection:
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def capture(_self: HttpClient, method: str, url: str, **options: Any) -> HttpResponse:
        options["cancel_token"].raise_if_cancelled()
        requests.append((method, url, options))
        return HttpResponse(200, b"{}", ())

    monkeypatch.setattr(HttpClient, "send", capture)
    collector = UsageCollector(
        tmp_path,
        UsageConfiguration("https://usage.test/v1/usage", True),
        "1.2.2",
        "linux",
        today=lambda: "2026-11-05",
    )
    return Collection(collector, requests, tmp_path)


@pytest.mark.parametrize("choice", ["unselected", "declined"])
def test_no_consent_creates_no_http_request_or_daily_code(
    collection: Collection, choice: str
) -> None:
    save_settings(collection.config_dir, Settings(usage_choice_v1=choice))
    collection.collector.resume()
    assert collection.collector.new_attempt() is None
    assert collection.requests == []
    assert not (collection.config_dir / "usage-day.json").exists()


def test_payload_allowlist_and_same_day_restart_deduplication(collection: Collection) -> None:
    save_settings(collection.config_dir, Settings(usage_choice_v1="accepted"))
    collection.collector.resume()
    attempt = collection.collector.new_attempt()
    assert attempt is not None
    collection.collector.send_active(attempt)
    collection.collector.send_active(attempt)
    assert len(collection.requests) == 1
    method, url, options = collection.requests[0]
    payload = json.loads(options["body"])
    assert method == "POST" and url == "https://usage.test/v1/usage"
    assert set(payload) == {
        "schema_version",
        "event",
        "day",
        "launcher_version",
        "os_group",
        "daily_id",
    }
    assert payload["event"] == "installation_active" and len(payload["daily_id"]) == 32
    assert options["headers"] == {"Content-Type": "application/json"}
    reopened = UsageCollector(
        collection.config_dir,
        collection.collector.configuration,
        "1.2.3",
        "windows",
        today=lambda: "2026-11-05",
    )
    reopened.resume()
    assert reopened.new_attempt() is None
    assert load_settings(collection.config_dir).usage_choice_v1 == "accepted"


def test_disable_cancels_queued_work_even_after_enabling_again(collection: Collection) -> None:
    save_settings(collection.config_dir, Settings(usage_choice_v1="accepted"))
    collection.collector.resume()
    attempt = collection.collector.new_attempt()
    assert attempt is not None
    save_settings(collection.config_dir, Settings(usage_choice_v1="declined"))
    collection.collector.revoke()
    save_settings(collection.config_dir, Settings(usage_choice_v1="accepted"))
    collection.collector.resume()
    collection.collector.send_active(attempt)
    assert collection.requests == [] and attempt.cancel_token.is_cancelled()
    assert not (collection.config_dir / "usage-day.json").exists()
    current = collection.collector.new_attempt()
    assert current is not None
    collection.collector.send_active(current)
    assert len(collection.requests) == 1
    save_settings(collection.config_dir, Settings(usage_choice_v1="declined"))
    collection.collector.revoke()
    assert not (collection.config_dir / "usage-day.json").exists()


def test_consent_is_rechecked_immediately_before_transport(
    collection: Collection, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_settings(collection.config_dir, Settings(usage_choice_v1="accepted"))
    collection.collector.resume()
    attempt = collection.collector.new_attempt()
    assert attempt is not None

    def stopped_client() -> HttpClient:
        save_settings(collection.config_dir, Settings(usage_choice_v1="declined"))
        collection.collector.revoke()
        return HttpClient()

    monkeypatch.setattr(collection.collector, "_make_http_client", stopped_client)
    collection.collector.send_active(attempt)
    assert collection.requests == []
    assert not (collection.config_dir / "usage-day.json").exists()


def test_day_rollover_uses_new_random_code_without_hardware_identity(
    collection: Collection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden() -> int:
        raise AssertionError("hardware identity must not be consulted")

    monkeypatch.setattr(uuid, "getnode", forbidden)
    day = ["2026-11-05"]
    monkeypatch.setattr(collection.collector, "_today", lambda: day[0])
    save_settings(collection.config_dir, Settings(usage_choice_v1="accepted"))
    collection.collector.resume()
    first = collection.collector.new_attempt()
    assert first is not None
    collection.collector.send_active(first)
    day[0] = "2026-11-06"
    second = collection.collector.new_attempt()
    assert second is not None
    collection.collector.send_active(second)
    payloads = [json.loads(options["body"]) for _, _, options in collection.requests]
    assert payloads[0]["daily_id"] != payloads[1]["daily_id"]
    assert [payload["day"] for payload in payloads] == ["2026-11-05", "2026-11-06"]


def test_network_failure_is_silent_and_does_not_schedule_retry(
    collection: Collection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(_self: HttpClient, *_args: Any, **_options: Any) -> HttpResponse:
        raise NetworkError("offline")

    monkeypatch.setattr(HttpClient, "send", unavailable)
    save_settings(collection.config_dir, Settings(usage_choice_v1="accepted"))
    collection.collector.resume()
    attempt = collection.collector.new_attempt()
    assert attempt is not None
    collection.collector.send_active(attempt)
    assert collection.collector.new_attempt() is None
    collection.collector.shutdown()
    assert collection.collector.new_attempt() is None
