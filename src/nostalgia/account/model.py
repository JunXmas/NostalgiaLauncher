"""Hai khái niệm cố tình tách rời: tài khoản lưu lâu dài, và danh tính để dựng lệnh.

`Account` là thứ **nằm trên đĩa** — có thể chứa vé đăng nhập, sống qua nhiều lần chạy.
`PlayerProfile` là thứ **dựng lệnh java cần** — rút ra từ `Account`, không bao giờ ghi đĩa.

Vì sao phải tách: khi thêm tài khoản Microsoft ở M2, `Account` mọc thêm vé làm mới, hạn dùng
và mã Xbox, còn `PlayerProfile` thì **không đổi một trường nào**. Nhờ vậy toàn bộ `launch/`
không phải sửa. Gộp hai thứ làm một là buộc phần dựng lệnh phải biết về OAuth.
"""

from __future__ import annotations

from dataclasses import dataclass

# Hai giá trị này đi vào lệnh java qua ${user_type}. Mojang chờ đúng chuỗi này.
OFFLINE = "offline"
MICROSOFT = "microsoft"

# Vé giả cho tài khoản offline. Game không kiểm nó khi chơi một mình, nhưng bỏ trống thì một
# số bản đời cũ hiểu nhầm là thiếu tham số và tự thoát.
OFFLINE_ACCESS_TOKEN = "0"


@dataclass(frozen=True, slots=True)
class Account:
    """Một tài khoản đã lưu. `access_token` rỗng với tài khoản offline."""

    player_name: str
    player_uuid: str
    account_kind: str
    access_token: str = ""
    # Chỉ tài khoản Microsoft mới có. `refresh_token` là thứ giữ cho lần chơi sau khỏi phải
    # nhập lại mã; `expires_at` là mốc epoch mà `access_token` hết hiệu lực (0 = không biết).
    refresh_token: str = ""
    expires_at: float = 0.0

    def __repr__(self) -> str:
        """Che CẢ HAI vé. `repr` hay rơi vào log và vào thông báo lỗi.

        Vé làm mới còn nguy hiểm hơn vé thường: nó sống hàng tháng và đổi được vé mới bất cứ
        lúc nào, nên lộ nó là mất tài khoản chứ không chỉ mất một phiên.
        """
        return (
            f"Account(player_name={self.player_name!r}, player_uuid={self.player_uuid!r}, "
            f"account_kind={self.account_kind!r}, "
            f"access_token={'***' if self.access_token else ''!r}, "
            f"refresh_token={'***' if self.refresh_token else ''!r}, "
            f"expires_at={self.expires_at!r})"
        )


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    """Danh tính đưa vào lệnh java. Không ghi đĩa, không chứa gì ngoài bốn thứ này."""

    player_name: str
    player_uuid: str
    access_token: str
    user_type: str

    @property
    def undashed_uuid(self) -> str:
        """Minecraft chờ UUID **không gạch** ở `${auth_uuid}`.

        Đưa bản có gạch vào thì game khởi động được nhưng skin và thống kê gắn nhầm chỗ —
        loại lỗi im lặng, chỉ lộ ra sau nhiều giờ chơi.
        """
        return self.player_uuid.replace("-", "")

    def __repr__(self) -> str:
        return (
            f"PlayerProfile(player_name={self.player_name!r}, "
            f"player_uuid={self.player_uuid!r}, access_token='***', "
            f"user_type={self.user_type!r})"
        )


def to_player_profile(account: Account) -> PlayerProfile:
    """Rút danh tính từ tài khoản đã lưu."""
    return PlayerProfile(
        player_name=account.player_name,
        player_uuid=account.player_uuid,
        access_token=account.access_token or OFFLINE_ACCESS_TOKEN,
        user_type=account.account_kind,
    )
