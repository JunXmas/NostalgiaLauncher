"""Tài khoản Ely.by trên đĩa: dựng từ lần đăng nhập, làm mới trước mỗi lần chạy."""

from __future__ import annotations

from nostalgia.account.model import ELY, Account
from nostalgia.auth.ely import ElyLogin, refresh_ely
from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS, AuthEndpoints
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


def build_ely_account(login: ElyLogin) -> Account:
    return Account(
        player_name=login.player_name,
        player_uuid=login.player_uuid,
        account_kind=ELY,
        access_token=login.access_token,
        client_token=login.client_token,
    )


def refresh_ely_account(
    http_client: HttpClient,
    account: Account,
    *,
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> Account:
    """Ely không cho biết hạn vé, nên làm mới mỗi lần chạy (một POST nhỏ). CHẠM MẠNG."""
    login = refresh_ely(
        http_client,
        account.access_token,
        account.client_token,
        endpoints=endpoints,
        cancel_token=cancel_token,
    )
    return build_ely_account(login)
