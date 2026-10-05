"""UUID offline: cùng tên phải ra cùng UUID, mãi mãi, trên mọi máy."""

from __future__ import annotations

import uuid

import pytest

from nostalgia.account.model import MICROSOFT, OFFLINE, OFFLINE_ACCESS_TOKEN, to_player_profile
from nostalgia.account.offline import build_offline_account, offline_uuid
from nostalgia.errors import AccountError

# Giá trị vàng: đối chiếu với `UUID.nameUUIDFromBytes("OfflinePlayer:Notch")` của Java, tức
# đúng công thức máy chủ Minecraft dùng. Sai một bit là người chơi mất thế giới.
NOTCH_UUID = "b50ad385-829d-3141-a216-7e7d7539ba7f"


def test_matches_the_value_a_minecraft_server_computes() -> None:
    assert offline_uuid("Notch") == NOTCH_UUID
    assert offline_uuid("jeb_") == "a762f560-4fce-3236-812a-b80efff0b62b"


def test_the_same_name_always_gives_the_same_uuid() -> None:
    """Nếu chỗ này ngẫu nhiên, mỗi lần chơi là một người mới: rương trống, tiến độ mất."""
    assert offline_uuid("Jun") == offline_uuid("Jun")
    assert offline_uuid("Jun") != offline_uuid("jun"), "phân biệt hoa thường, như Mojang"


def test_it_is_not_the_namespaced_uuid3_of_python() -> None:
    """`uuid.uuid3` chèn 16 byte không gian tên vào trước — ra giá trị khác hẳn.

    Đây là cái bẫy sẵn nhất: `uuid3` trông đúng, chạy được, và sai lặng lẽ.
    """
    wrong = str(uuid.uuid3(uuid.NAMESPACE_DNS, "OfflinePlayer:Notch"))
    assert offline_uuid("Notch") != wrong


def test_the_version_and_variant_bits_are_set() -> None:
    parsed = uuid.UUID(offline_uuid("Notch"))
    assert parsed.version == 3
    assert parsed.variant == uuid.RFC_4122


def test_an_account_carries_the_name_the_uuid_and_the_kind() -> None:
    account = build_offline_account("Notch")
    assert account.player_name == "Notch"
    assert account.player_uuid == NOTCH_UUID
    assert account.account_kind == OFFLINE
    assert account.access_token == "", "tài khoản offline không có vé thật"


@pytest.mark.parametrize(
    "player_name", ["", "ab", "a" * 17, "có dấu", "hai từ", "dấu-gạch", "Jun!", "Jun\n"]
)
def test_names_minecraft_would_reject_are_refused_up_front(player_name: str) -> None:
    """Báo lúc thêm tài khoản, chứ không phải lúc game đã chạy rồi tự thoát không nói gì."""
    with pytest.raises(AccountError, match="không hợp lệ"):
        build_offline_account(player_name)


@pytest.mark.parametrize("player_name", ["Jun", "abc", "a" * 16, "Player_1", "___"])
def test_names_minecraft_accepts_are_allowed(player_name: str) -> None:
    assert build_offline_account(player_name).player_name == player_name


def test_the_profile_hands_the_command_an_undashed_uuid() -> None:
    """`${auth_uuid}` chờ bản không gạch; đưa bản có gạch thì skin gắn nhầm chỗ."""
    player_profile = to_player_profile(build_offline_account("Notch"))
    assert player_profile.undashed_uuid == "b50ad385829d3141a2167e7d7539ba7f"
    assert "-" not in player_profile.undashed_uuid
    assert player_profile.player_uuid == NOTCH_UUID, "bản có gạch vẫn giữ nguyên để hiển thị"


def test_an_offline_profile_gets_a_placeholder_token() -> None:
    """Vài bản đời cũ hiểu vé rỗng là thiếu tham số rồi tự thoát."""
    player_profile = to_player_profile(build_offline_account("Jun"))
    assert player_profile.access_token == OFFLINE_ACCESS_TOKEN
    assert player_profile.user_type == OFFLINE


def test_a_real_token_is_carried_through_untouched() -> None:
    """M2 sẽ đưa vé Microsoft thật vào đây; `launch/` không được sửa dòng nào."""
    from nostalgia.account.model import Account

    account = Account(
        player_name="Jun", player_uuid=NOTCH_UUID, account_kind=MICROSOFT, access_token="ve-that"
    )
    assert to_player_profile(account).access_token == "ve-that"


def test_repr_never_leaks_the_token() -> None:
    """`repr` rơi vào log và vào thông báo lỗi — chỗ vé đăng nhập hay bị lộ nhất."""
    from nostalgia.account.model import Account

    account = Account(
        player_name="Jun", player_uuid=NOTCH_UUID, account_kind=MICROSOFT, access_token="bi-mat"
    )
    assert "bi-mat" not in repr(account)
    assert "***" in repr(account)
    assert "bi-mat" not in repr(to_player_profile(account))
    assert "Jun" in repr(account), "phần không bí mật vẫn phải đọc được để gỡ lỗi"
