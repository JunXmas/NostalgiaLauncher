"""Gửi best-effort tối đa một lần/ngày, kiểm quyền ngay trước HTTP và hủy theo thế hệ."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from nostalgia.errors import NostalgiaError
from nostalgia.model.usage import UsagePayload
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.settings.store import load_settings
from nostalgia.usage.configuration import UsageConfiguration
from nostalgia.usage.state import UsageDay, load_usage_day, save_usage_day


@dataclass(frozen=True, slots=True)
class UsageAttempt:
    generation: int
    cancel_token: CancelToken


def utc_day() -> str:
    return datetime.now(UTC).date().isoformat()


def usage_http_client() -> HttpClient:
    return HttpClient(timeout_seconds=3)


class UsageCollector:
    def __init__(
        self,
        config_dir: Path,
        configuration: UsageConfiguration,
        launcher_version: str,
        os_group: str,
        *,
        make_http_client: Callable[[], HttpClient] = usage_http_client,
        today: Callable[[], str] = utc_day,
    ) -> None:
        self.configuration = configuration
        self._config_dir = config_dir
        self._state_path = config_dir / "usage-day.json"
        self._launcher_version = launcher_version
        self._os_group = {"osx": "macos"}.get(os_group, os_group)
        if self._os_group not in ("windows", "linux", "macos"):
            self._os_group = "other"
        self._make_http_client, self._today = make_http_client, today
        self._lock = threading.RLock()
        self._generation, self._armed = 0, False
        self._token = CancelToken()

    def resume(self) -> None:
        with self._lock:
            self._token.cancel()
            self._token = CancelToken()
            self._generation += 1
            self._armed = self.configuration.ready

    def revoke(self) -> None:
        with self._lock:
            self.shutdown()
            self._state_path.unlink(missing_ok=True)

    def shutdown(self) -> None:
        with self._lock:
            self._armed = False
            self._generation += 1
            self._token.cancel()

    def _allowed(self, attempt: UsageAttempt) -> bool:
        return (
            self._armed
            and self.configuration.ready
            and attempt.generation == self._generation
            and not attempt.cancel_token.is_cancelled()
            and load_settings(self._config_dir).usage_choice_v1 == "accepted"
        )

    def new_attempt(self) -> UsageAttempt | None:
        with self._lock:
            attempt = UsageAttempt(self._generation, self._token)
            if not self._allowed(attempt):
                return None
            state = load_usage_day(self._state_path)
            return None if state and state.day == self._today() and state.attempted else attempt

    def send_active(self, attempt: UsageAttempt) -> None:
        try:
            with self._lock:
                if not self._allowed(attempt):
                    return
                day = self._today()
                state = load_usage_day(self._state_path)
                if state and state.day == day and state.attempted:
                    return
                daily_id = state.daily_id if state and state.day == day else secrets.token_hex(16)
                payload = UsagePayload(day, self._launcher_version, self._os_group, daily_id)
                save_usage_day(self._state_path, UsageDay(day, daily_id, True))
            with self._make_http_client() as http_client:
                with self._lock:
                    if not self._allowed(attempt):
                        return
                http_client.send(
                    "POST",
                    self.configuration.endpoint,
                    body=payload.json_text().encode(),
                    headers={"Content-Type": "application/json"},
                    max_bytes=1024,
                    cancel_token=attempt.cancel_token,
                )
        except (NostalgiaError, OSError, ValueError):
            # Thống kê lỗi không ảnh hưởng chơi game, không tạo retry hay popup.
            return
