"""Phiên Google trong kho bí mật OS, tuyệt đối không fallback sang JSON/plaintext."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from pathlib import Path
from typing import Any

from nostalgia.net.session_proof import forget_session, register_session, session_seed


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
            if isinstance(value, str) and value.startswith("{"):
                document = json.loads(value)
                access_token, seed = document["access_token"], document["proof_seed"]
                if (
                    not isinstance(access_token, str)
                    or not isinstance(seed, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", seed)
                ):
                    return ""
                register_session(access_token, seed)
                value = access_token
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
            seed = session_seed(access_token)
            credential = (
                json.dumps({"access_token": access_token, "proof_seed": seed})
                if seed
                else access_token
            )
            self._backend.set_password(self._service, "session", credential)
            return True
        except Exception:
            return False

    def remove_access_token(self) -> None:
        forget_session(self.load_access_token())
        try:
            if self._backend:
                self._backend.delete_password(self._service, "session")
        except Exception:
            pass
