"""Phiên Google trong kho bí mật OS, tuyệt đối không fallback sang JSON/plaintext."""

from __future__ import annotations

import hashlib
import importlib
import re
from pathlib import Path
from typing import Any


class KeyringSessionStore:
    def __init__(self, service_url: str, config_dir: Path) -> None:
        scope = hashlib.sha256(
            (service_url.rstrip("/") + "\n" + str(config_dir.absolute())).encode()
        ).hexdigest()
        self._service = "Nostalgia.Google." + scope
        self._backend: Any = None
        try:
            keyring_module = importlib.import_module("keyring")
            backend = keyring_module.get_keyring()
            # Loại bỏ plaintext/chainer không xác định của keyrings.alt hoặc cấu hình máy.
            if (
                type(backend).__module__
                in {
                    "keyring.backends.Windows",
                    "keyring.backends.macOS",
                    "keyring.backends.SecretService",
                    "keyring.backends.kwallet",
                }
                and backend.priority > 0
            ):
                self._backend = backend
        except Exception:
            pass

    def load_access_token(self) -> str:
        try:
            value = self._backend.get_password(self._service, "session") if self._backend else ""
            return (
                value
                if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{32,256}", value)
                else ""
            )
        except Exception:
            return ""

    def save_access_token(self, access_token: str) -> bool:
        if not self._backend or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", access_token):
            return False
        try:
            self._backend.set_password(self._service, "session", access_token)
            return True
        except Exception:
            return False

    def remove_access_token(self) -> None:
        try:
            if self._backend:
                self._backend.delete_password(self._service, "session")
        except Exception:
            pass
