"""Phần dây nối CLI cho tài khoản Microsoft.

Giao thức đã được kiểm trọn ở `tests/auth`; ở đây chỉ kiểm CLI có gọi đúng chỗ, in đúng thứ
người dùng cần thấy, lưu đúng thứ cần lưu, và phân biệt đúng hai kiểu hỏng.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cli_fixture import INSTANCE_ID, install_and_create_instance, make_paths, roots
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import MICROSOFT, Account
from nostalgia.account.store import find_account, load_accounts, save_accounts
from nostalgia.auth import microsoft as auth_microsoft
from nostalgia.auth.device_code import DeviceCode, MicrosoftTokens
from nostalgia.auth.endpoints import CLIENT_ID_ENV
from nostalgia.auth.microsoft import DeviceCodeFn, MicrosoftLogin, ignore_device_code
from nostalgia.auth.minecraft import MinecraftSession
from nostalgia.cli.main import main
from nostalgia.errors import NetworkError
from nostalgia.net.http import HttpClient

DASHED_UUID = "b50ad385-829d-3141-a216-7e7d7539ba7f"


def make_login(*, owns_game: bool = True, expires_in: int = 3600) -> MicrosoftLogin:
    return MicrosoftLogin(
        minecraft_session=MinecraftSession(
            access_token="ve-minecraft",
            owns_game=owns_game,
            player_uuid=DASHED_UUID if owns_game else "",
            player_name="Notch" if owns_game else "",
        ),
        tokens=MicrosoftTokens(
            access_token="ve-ms", refresh_token="ve-lam-moi", expires_in_seconds=expires_in
        ),
    )


def test_signing_in_without_a_client_id_says_exactly_what_to_register(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Không có mã ứng dụng là chuyện thường gặp nhất; thông báo phải là hướng dẫn."""
    assert main([*roots(tmp_path), "account", "add-microsoft"]) == 1

    captured = capsys.readouterr().err
    assert "portal.azure.com" in captured
    assert "mce-reviewappid" in captured
    assert CLIENT_ID_ENV in captured


def test_signing_in_shows_the_code_and_saves_the_account(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CLIENT_ID_ENV, "ma-ung-dung")
    shown: list[DeviceCode] = []

    def fake_sign_in(
        _http_client: HttpClient,
        _client_id: str,
        on_device_code: DeviceCodeFn = ignore_device_code,
        **_kwargs: object,
    ) -> MicrosoftLogin:
        device_code = DeviceCode(
            user_code="ABCD-EFGH",
            verification_url="https://microsoft.com/link",
            device_code="bi-mat",
        )
        shown.append(device_code)
        on_device_code(device_code)
        return make_login()

    monkeypatch.setattr(auth_microsoft, "sign_in", fake_sign_in)

    assert main([*roots(tmp_path), "account", "add-microsoft"]) == 0

    printed = capsys.readouterr().out
    assert "https://microsoft.com/link" in printed
    assert "ABCD-EFGH" in printed
    assert "bi-mat" not in printed, "mã bí mật không được in ra"

    saved = load_accounts(make_paths(tmp_path).accounts_json)
    assert [account.player_name for account in saved] == ["Notch"]
    assert saved[0].account_kind == MICROSOFT
    assert saved[0].refresh_token == "ve-lam-moi"
    assert saved[0].expires_at > time.time()


def test_an_account_without_the_game_is_saved_but_flagged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CLIENT_ID_ENV, "ma-ung-dung")
    monkeypatch.setattr(
        auth_microsoft, "sign_in", lambda *_args, **_kwargs: make_login(owns_game=False)
    )

    assert main([*roots(tmp_path), "account", "add-microsoft"]) == 0
    assert "CHƯA MUA" in capsys.readouterr().out
    assert load_accounts(make_paths(tmp_path).accounts_json)[0].player_name == "Demo"


def save_stale_account(tmp_path: Path) -> None:
    save_accounts(
        make_paths(tmp_path).accounts_json,
        (
            Account(
                player_name="Notch",
                player_uuid=DASHED_UUID,
                account_kind=MICROSOFT,
                access_token="ve-cu",
                refresh_token="ve-lam-moi",
                expires_at=1.0,
            ),
        ),
    )


def test_playing_refreshes_a_stale_token_and_saves_the_new_one(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_and_create_instance(server, server_state, http_client, tmp_path)
    save_stale_account(tmp_path)
    monkeypatch.setenv(CLIENT_ID_ENV, "ma-ung-dung")

    def fake_refresh(
        _http_client: HttpClient,
        _client_id: str,
        account: Account,
        *,
        now: float,
        **_kwargs: object,
    ) -> Account:
        return Account(
            player_name=account.player_name,
            player_uuid=account.player_uuid,
            account_kind=MICROSOFT,
            access_token="ve-moi",
            refresh_token="ve-lam-moi-2",
            expires_at=now + 3600,
        )

    from nostalgia.account import microsoft as account_microsoft

    monkeypatch.setattr(account_microsoft, "refresh_account", fake_refresh)
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Notch"]) == 0

    assert "đang làm mới" in capsys.readouterr().out
    saved = find_account(load_accounts(make_paths(tmp_path).accounts_json), "Notch")
    assert saved is not None
    assert saved.access_token == "ve-moi"
    assert saved.refresh_token == "ve-lam-moi-2"


def test_playing_without_network_warns_but_still_tries(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mất mạng chưa chắc vé đã hỏng — chơi một mình thì thường vẫn vào được."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    save_stale_account(tmp_path)
    monkeypatch.setenv(CLIENT_ID_ENV, "ma-ung-dung")

    def explode(*_args: object, **_kwargs: object) -> Account:
        message = "không gọi được máy chủ"
        raise NetworkError(message)

    from nostalgia.account import microsoft as account_microsoft

    monkeypatch.setattr(account_microsoft, "refresh_account", explode)
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Notch"]) == 0

    assert "không làm mới được vé" in capsys.readouterr().err


def test_a_dead_refresh_token_stops_the_launch(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Khác hẳn mất mạng: vé chết là dứt khoát, để Minecraft báo hộ thì khó hiểu hơn nhiều."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    save_stale_account(tmp_path)
    monkeypatch.setenv(CLIENT_ID_ENV, "ma-ung-dung")

    def explode(*_args: object, **_kwargs: object) -> Account:
        from nostalgia.errors import AuthError

        message = "vé làm mới đã hết hiệu lực — cần đăng nhập lại"
        raise AuthError(message)

    from nostalgia.account import microsoft as account_microsoft

    monkeypatch.setattr(account_microsoft, "refresh_account", explode)
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Notch"]) == 1
    assert "đăng nhập lại" in capsys.readouterr().err


def test_an_offline_account_never_triggers_a_refresh(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_and_create_instance(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Jun"]) == 0
    assert "làm mới" not in capsys.readouterr().out
