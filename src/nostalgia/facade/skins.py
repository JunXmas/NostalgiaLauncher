"""Thao tác skin: đọc cache (nhanh, cho giao diện vẽ ngay), làm mới, và upload lên Mojang."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.account.model import ELY, MICROSOFT, Account
from nostalgia.errors import AccountError
from nostalgia.facade.context import LauncherContext
from nostalgia.skin.model import PlayerSkin
from nostalgia.skin.textures import cached_skin, refresh_ely_skin, refresh_premium_skin
from nostalgia.skin.upload import upload_skin_to_mojang


@dataclass(frozen=True, slots=True)
class SkinOperations(LauncherContext):
    def describe_skin(self, account: Account) -> PlayerSkin:
        """Chỉ đọc đĩa. Chưa có cache thì Steve/Alex theo UUID."""
        return cached_skin(self.paths.skins_dir, _cache_key(account), account.player_uuid)

    def refresh_skin(self, account: Account) -> PlayerSkin:
        """CHẠM MẠNG cho Microsoft và Ely.by; tài khoản ngoại tuyến thì như `describe_skin`."""
        with self.make_http_client() as http_client:
            if account.account_kind == MICROSOFT:
                return refresh_premium_skin(
                    http_client, self.paths.skins_dir, account.player_uuid, endpoints=self.endpoints
                )
            if account.account_kind == ELY:
                return refresh_ely_skin(
                    http_client,
                    self.paths.skins_dir,
                    account.player_name,
                    account.player_uuid,
                    endpoints=self.endpoints,
                )
        return self.describe_skin(account)

    def upload_skin(self, account: Account, skin_path: Path, *, slim: bool = False) -> PlayerSkin:
        """Upload skin mới lên Mojang (chỉ tài khoản Microsoft). CHẠM MẠNG.

        Sau khi upload thành công, tải lại skin từ server để cập nhật cache.
        """
        if account.account_kind != MICROSOFT:
            raise AccountError("chỉ tài khoản Microsoft mới upload được skin lên Mojang")
        if not account.access_token:
            raise AccountError("tài khoản chưa đăng nhập hoặc vé hết hạn — đăng nhập lại")
        with self.make_http_client() as http_client:
            upload_skin_to_mojang(http_client, account.access_token, skin_path, slim=slim)
            return refresh_premium_skin(
                http_client, self.paths.skins_dir, account.player_uuid, endpoints=self.endpoints
            )


def _cache_key(account: Account) -> str:
    if account.account_kind == ELY:
        return f"ely-{account.player_name.lower()}"
    return account.player_uuid.replace("-", "")
