"""Tài khoản: ngoại tuyến, Microsoft, làm mới vé."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import replace

from nostalgia.account.ely import build_ely_account, refresh_ely_account
from nostalgia.account.microsoft import build_microsoft_account, needs_refresh, refresh_account
from nostalgia.account.model import ELY, Account
from nostalgia.account.offline import build_offline_account
from nostalgia.account.store import (
    find_account,
    load_accounts,
    remove_account,
    save_accounts,
    upsert_account,
)
from nostalgia.auth.ely import sign_in_ely
from nostalgia.auth.ely_web import ElyWebEndpoints, sign_in_ely_web
from nostalgia.auth.microsoft import DeviceCodeFn, ignore_device_code, resolve_client_id, sign_in
from nostalgia.errors import AccountError
from nostalgia.facade.context import LauncherContext
from nostalgia.operations.cancellation import CancelToken

logger = logging.getLogger(__name__)


class AccountOperations(LauncherContext):
    __slots__ = ()

    def list_accounts(self) -> tuple[Account, ...]:
        return load_accounts(self.paths.accounts_json)

    def add_offline_account(self, player_name: str) -> Account:
        return self._store(build_offline_account(player_name))

    def add_microsoft_account(
        self,
        client_id: str = "",
        *,
        on_device_code: DeviceCodeFn = ignore_device_code,
        cancel_token: CancelToken | None = None,
    ) -> Account:
        """Đăng nhập Microsoft. CHẠM MẠNG, và chờ người dùng nhập mã trên trang của họ.

        Không truyền `client_id` thì dùng app đã duyệt của launcher — giao diện không cần
        biết khái niệm này tồn tại.
        """
        with self.make_http_client() as http_client:
            login = sign_in(
                http_client,
                client_id or resolve_client_id(os.environ),
                on_device_code,
                endpoints=self.auth_endpoints,
                cancel_token=cancel_token,
            )
        return self._store(build_microsoft_account(login, now=time.time()))

    def add_ely_account(
        self,
        email_or_name: str,
        password: str,
        *,
        totp_code: str = "",
        cancel_token: CancelToken | None = None,
    ) -> Account:
        """Đăng nhập Ely.by (non-premium). CHẠM MẠNG. Mật khẩu không lưu; ném
        `TwoFactorRequired` khi tài khoản bật 2FA mà chưa có mã.

        Đăng nhập luôn cả phiên WEB account.ely.by bằng đúng thông tin vừa gõ để giữ
        `refresh_token` — đó là thứ cho phép đổi skin thật từ launcher về sau mà không
        hỏi lại mật khẩu. Phần web hỏng thì vẫn vào game được, chỉ mất tính năng đổi skin,
        nên chỉ log warning chứ không ném.
        """
        with self.make_http_client() as http_client:
            login = sign_in_ely(
                http_client,
                email_or_name,
                password,
                totp_code=totp_code,
                endpoints=self.auth_endpoints,
                cancel_token=cancel_token,
            )
            web_refresh_token = ""
            try:
                web_session = sign_in_ely_web(
                    http_client,
                    email_or_name,
                    password,
                    totp_code=totp_code,
                    endpoints=self.ely_web_endpoints(),
                    cancel_token=cancel_token,
                )
                web_refresh_token = web_session.refresh_token
            except AccountError as exc:
                logger.warning(
                    "không mở được phiên web Ely.by (đổi skin sẽ cần đăng nhập lại): %s", exc
                )
        account = build_ely_account(login)
        if web_refresh_token:
            account = replace(account, refresh_token=web_refresh_token)
        return self._store(account)

    def ely_web_endpoints(self) -> ElyWebEndpoints:
        return ElyWebEndpoints(
            account_root=self.auth_endpoints.ely_web_account_root,
            site_root=self.auth_endpoints.ely_web_site_root,
        )

    def remove_account(self, account_id: str) -> None:
        """Gỡ một tài khoản. Nhận `account_id` (`kind:uuid`) hoặc tên; tên trùng thì gỡ cái
        đầu tiên, nên giao diện luôn truyền `account_id`."""
        accounts = self.list_accounts()
        if find_account(accounts, account_id) is None:
            message = f"không có tài khoản {account_id!r}"
            raise AccountError(message)
        save_accounts(self.paths.accounts_json, remove_account(accounts, account_id))

    def _require_account(
        self, account_id: str, client_id: str, cancel_token: CancelToken | None
    ) -> Account:
        account = find_account(self.list_accounts(), account_id)
        if account is None:
            message = f"không có tài khoản {account_id!r}"
            raise AccountError(message)
        if account.account_kind == ELY:
            with self.make_http_client() as http_client:
                return self._store(
                    refresh_ely_account(
                        http_client,
                        account,
                        endpoints=self.auth_endpoints,
                        cancel_token=cancel_token,
                    )
                )
        if not needs_refresh(account, now=time.time()):
            return account
        with self.make_http_client() as http_client:
            refreshed = refresh_account(
                http_client,
                client_id or resolve_client_id(os.environ),
                account,
                now=time.time(),
                endpoints=self.auth_endpoints,
                cancel_token=cancel_token,
            )
        return self._store(refreshed)

    def _store(self, account: Account) -> Account:
        save_accounts(self.paths.accounts_json, upsert_account(self.list_accounts(), account))
        return account
