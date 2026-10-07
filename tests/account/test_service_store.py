"""Kho phiên chỉ dùng backend an toàn; không ghi token vào cấu hình launcher."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from nostalgia.account import service_store


class VaultFixture:
    priority = 1

    def __init__(self) -> None:
        self.credentials: dict[tuple[str, str], str] = {}

    def read_password(self, service: str, account_id: str) -> str:
        return self.credentials.get((service, account_id), "")

    get_password = read_password

    def set_password(self, service: str, account_id: str, access_token: str) -> None:
        self.credentials[service, account_id] = access_token

    def delete_password(self, service: str, account_id: str) -> None:
        self.credentials.pop((service, account_id), None)


def test_safe_vault_is_scoped_to_endpoint_and_installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = VaultFixture()
    monkeypatch.setattr(VaultFixture, "__module__", "keyring.backends.Windows")
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _name: SimpleNamespace(get_keyring=lambda: vault),
    )
    store = service_store.KeyringSessionStore("https://accounts.test", tmp_path)
    assert store.save_access_token("a" * 64)
    assert store.load_access_token() == "a" * 64
    assert not service_store.KeyringSessionStore("https://other.test", tmp_path).load_access_token()
    assert not service_store.KeyringSessionStore(
        "https://accounts.test", tmp_path / "other"
    ).load_access_token()
    assert not list(tmp_path.iterdir())
    store.remove_access_token()
    assert not store.load_access_token()


def test_plaintext_backend_refused_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = VaultFixture()
    monkeypatch.setattr(VaultFixture, "__module__", "keyrings.alt.file")
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _name: SimpleNamespace(get_keyring=lambda: vault),
    )
    store = service_store.KeyringSessionStore("https://accounts.test", tmp_path)
    assert not store.save_access_token("a" * 64)
    assert not store.load_access_token() and not vault.credentials
    assert not list(tmp_path.iterdir())


def test_bound_session_restores_its_signing_key_only_from_secure_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nostalgia.net.session_proof import (
        forget_session,
        proof_headers,
        register_session,
        session_seed,
    )

    vault = VaultFixture()
    monkeypatch.setattr(VaultFixture, "__module__", "keyring.backends.Windows")
    monkeypatch.setattr(
        importlib, "import_module", lambda _name: SimpleNamespace(get_keyring=lambda: vault)
    )
    access_token = "vault_bound_" + "z" * 52
    register_session(access_token, "1b" * 32)
    store = service_store.KeyringSessionStore("https://accounts.test", tmp_path)
    assert store.save_access_token(access_token)
    forget_session(access_token)
    assert not proof_headers(access_token, "GET", "https://accounts.test/v1/me", None)
    assert store.load_access_token() == access_token
    assert session_seed(access_token) == "1b" * 32
    assert proof_headers(access_token, "GET", "https://accounts.test/v1/me", None)
    assert not list(tmp_path.iterdir())
    store.remove_access_token()
    assert not store.load_access_token() and not session_seed(access_token)
