"""Kho tài khoản: ghi nguyên tử, quyền 0600, và chịu được file hỏng."""

from __future__ import annotations

import json
import logging
import stat
from pathlib import Path

import pytest

from nostalgia.account.model import MICROSOFT, OFFLINE, Account
from nostalgia.account.offline import build_offline_account
from nostalgia.account.store import (
    find_account,
    load_accounts,
    remove_account,
    save_accounts,
    upsert_account,
)
from nostalgia.errors import DataFileError
from nostalgia.storage.paths import DataPaths


def make_accounts() -> tuple[Account, ...]:
    return tuple(build_offline_account(name) for name in ("Jun", "Notch", "jeb_"))


def test_a_saved_store_reads_back_identical(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    accounts = make_accounts()

    save_accounts(path, accounts)

    assert load_accounts(path) == accounts


def test_the_store_is_not_readable_by_other_users(tmp_path: Path) -> None:
    """File này sẽ chứa vé đăng nhập Microsoft ở M2."""
    path = tmp_path / "accounts.json"
    save_accounts(path, make_accounts())

    mode = stat.S_IMODE(path.stat().st_mode)

    assert mode == 0o600, f"quyền là {oct(mode)}"


def test_writing_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    save_accounts(path, make_accounts())
    save_accounts(path, make_accounts())

    assert [path_entry.name for path_entry in tmp_path.iterdir()] == ["accounts.json"]


def test_a_missing_store_is_empty_not_an_error(tmp_path: Path) -> None:
    assert load_accounts(tmp_path / "chua-co.json") == ()


def test_a_store_broken_at_the_json_level_refuses_to_load(tmp_path: Path) -> None:
    """Coi file hỏng như rỗng là con đường thẳng tới việc lần ghi sau xoá sạch tài khoản."""
    path = tmp_path / "accounts.json"
    path.write_text("{khong phai json", encoding="utf-8")

    with pytest.raises(DataFileError):
        load_accounts(path)


def test_one_broken_record_does_not_take_the_others_with_it(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "accounts.json"
    path.write_text(
        json.dumps(
            {
                "format": 1,
                "accounts": [
                    {"player_name": "Jun", "player_uuid": "u-1", "account_kind": OFFLINE},
                    {"player_name": "ThieuUuid"},
                    "khong phai doi tuong",
                    {"player_name": "Notch", "player_uuid": "u-2", "account_kind": OFFLINE},
                ],
            }
        ),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING):
        accounts = load_accounts(path)

    assert [account.player_name for account in accounts] == ["Jun", "Notch"]
    assert len(caplog.records) == 2, "bỏ qua thì phải nói, không được im lặng"


def test_an_unknown_field_does_not_break_reading(tmp_path: Path) -> None:
    """Bản sau có thể thêm trường; bản trước đọc vào không được nổ."""
    path = tmp_path / "accounts.json"
    path.write_text(
        json.dumps(
            {
                "format": 99,
                "accounts": [
                    {
                        "player_name": "Jun",
                        "player_uuid": "u-1",
                        "account_kind": OFFLINE,
                        "truong_moi": {"gi do": 1},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert load_accounts(path)[0].player_name == "Jun"


def test_a_token_survives_the_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    account = Account(
        player_name="Jun", player_uuid="u-1", account_kind=MICROSOFT, access_token="ve"
    )

    save_accounts(path, (account,))

    assert load_accounts(path)[0].access_token == "ve"


def test_lookup_ignores_letter_case_because_people_type_it() -> None:
    accounts = make_accounts()
    assert find_account(accounts, "jun") is not None
    assert find_account(accounts, "JUN") is not None
    assert find_account(accounts, "khong-co") is None
    assert find_account((), "Jun") is None


def test_adding_the_same_name_replaces_in_place_and_keeps_the_order() -> None:
    """Đăng nhập lại không nên làm tài khoản nhảy xuống cuối danh sách."""
    accounts = make_accounts()
    changed = Account(
        player_name="notch", player_uuid="u-moi", account_kind=MICROSOFT, access_token="ve"
    )

    updated = upsert_account(accounts, changed)

    assert [account.player_name for account in updated] == ["Jun", "notch", "jeb_"]
    assert len(updated) == len(accounts)
    assert updated[1].player_uuid == "u-moi"


def test_adding_a_new_name_appends() -> None:
    updated = upsert_account(make_accounts(), build_offline_account("Steve"))
    assert [account.player_name for account in updated][-1] == "Steve"
    assert len(updated) == 4


def test_removing_ignores_letter_case_and_missing_names() -> None:
    accounts = make_accounts()
    assert [account.player_name for account in remove_account(accounts, "NOTCH")] == ["Jun", "jeb_"]
    assert remove_account(accounts, "khong-co") == accounts
    assert remove_account((), "Jun") == ()


def test_the_store_lives_beside_the_config_not_the_downloads(tmp_path: Path) -> None:
    """Xoá `data_dir` để lấy chỗ trống thì không được mất tài khoản theo."""
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")

    assert paths.accounts_json == tmp_path / "config" / "accounts.json"
    assert not paths.accounts_json.is_relative_to(paths.data_dir)


def test_saving_creates_the_config_directory(tmp_path: Path) -> None:
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")

    save_accounts(paths.accounts_json, make_accounts())

    assert paths.accounts_json.exists()
