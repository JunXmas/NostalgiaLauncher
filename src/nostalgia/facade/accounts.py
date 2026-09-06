"""Tài khoản: ngoại tuyến, Microsoft, làm mới vé."""

from __future__ import annotations

import time

from nostalgia.account.microsoft import build_microsoft_account, needs_refresh, refresh_account
from nostalgia.account.model import Account
from nostalgia.account.offline import build_offline_account
from nostalgia.account.store import (
    find_account,
    load_accounts,
    remove_account,
    save_accounts,
    upsert_account,
)
from nostalgia.auth.microsoft import DeviceCodeFn, ignore_device_code, sign_in
from nostalgia.errors import AccountError
from nostalgia.facade.context import LauncherContext
from nostalgia.operations.cancellation import CancelToken


class AccountOperations(LauncherContext):
    __slots__ = ()

    def list_accounts(self) -> tuple[Account, ...]:
        return load_accounts(self.paths.accounts_json)

    def add_offline_account(self, player_name: str) -> Account:
        return self._store(build_offline_account(player_name))

    def add_microsoft_account(
        self,
        client_id: str,
        *,
        on_device_code: DeviceCodeFn = ignore_device_code,
        cancel_token: CancelToken | None = None,
    ) -> Account:
        """Đăng nhập Microsoft. CHẠM MẠNG, và chờ người dùng nhập mã trên trang của họ."""
        with self.make_http_client() as http_client:
            login = sign_in(
                http_client,
                client_id,
                on_device_code,
                endpoints=self.auth_endpoints,
                cancel_token=cancel_token,
            )
        return self._store(build_microsoft_account(login, now=time.time()))

    def remove_account(self, player_name: str) -> None:
        accounts = self.list_accounts()
        if find_account(accounts, player_name) is None:
            message = f"không có tài khoản {player_name!r}"
            raise AccountError(message)
        save_accounts(self.paths.accounts_json, remove_account(accounts, player_name))

    def _require_account(
        self, player_name: str, client_id: str, cancel_token: CancelToken | None
    ) -> Account:
        account = find_account(self.list_accounts(), player_name)
        if account is None:
            message = f"không có tài khoản {player_name!r}"
            raise AccountError(message)
        if not needs_refresh(account, now=time.time()):
            return account
        with self.make_http_client() as http_client:
            refreshed = refresh_account(
                http_client,
                client_id,
                account,
                now=time.time(),
                endpoints=self.auth_endpoints,
                cancel_token=cancel_token,
            )
        return self._store(refreshed)

    def _store(self, account: Account) -> Account:
        save_accounts(self.paths.accounts_json, upsert_account(self.list_accounts(), account))
        return account
