"""Thao tác skin: đọc cache (nhanh, cho giao diện vẽ ngay), làm mới, upload lên Mojang, và
kho skin của launcher — mọi skin từng tải về hay upload đều được giữ lại để chọn lại nhanh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.account.model import ELY, MICROSOFT, Account
from nostalgia.errors import AccountError, SkinError
from nostalgia.facade.accounts import AccountOperations
from nostalgia.operations.cancellation import CancelToken
from nostalgia.skin.library import (
    SkinEntry,
    add_to_library,
    digest_of_file,
    find_entry,
    list_library,
    remove_from_library,
)
from nostalgia.skin.model import PlayerSkin
from nostalgia.skin.textures import (
    cached_skin,
    refresh_ely_skin,
    refresh_premium_skin,
    skin_cache_key,
)
from nostalgia.skin.upload import upload_skin_to_mojang


@dataclass(frozen=True, slots=True)
class SkinOperations(AccountOperations):
    def describe_skin(self, account: Account) -> PlayerSkin:
        """Chỉ đọc đĩa. Chưa có cache thì Steve/Alex theo UUID."""
        return cached_skin(self.paths.skins_dir, _cache_key(account), account.player_uuid)

    def refresh_skin(self, account: Account) -> PlayerSkin:
        """CHẠM MẠNG cho Microsoft và Ely.by; tài khoản ngoại tuyến thì như `describe_skin`.
        Skin tải về (không phải mặc định) được cất vào kho skin của launcher."""
        if account.account_kind not in (MICROSOFT, ELY):
            return self.describe_skin(account)
        with self.make_http_client() as http_client:
            if account.account_kind == MICROSOFT:
                skin = refresh_premium_skin(
                    http_client, self.paths.skins_dir, account.player_uuid, endpoints=self.endpoints
                )
            else:
                skin = refresh_ely_skin(
                    http_client,
                    self.paths.skins_dir,
                    account.player_name,
                    account.player_uuid,
                    endpoints=self.endpoints,
                )
        if not skin.is_default:
            self._collect(
                skin.skin_path,
                name=account.player_name,
                slim=skin.slim,
                source=account.account_kind,
            )
        return skin

    # ----- kho skin -----

    def list_skin_library(self) -> tuple[SkinEntry, ...]:
        return list_library(self.paths.skins_dir)

    def import_skin(self, skin_path: Path, *, name: str = "", slim: bool = False) -> SkinEntry:
        """Đưa một file PNG vào kho (không đụng tài khoản nào)."""
        return add_to_library(
            self.paths.skins_dir, skin_path, name=name or skin_path.stem, slim=slim, source="import"
        )

    def skin_digest(self, skin: PlayerSkin) -> str:
        """Khoá nhận diện ảnh skin đang dùng; rỗng nếu là Steve/Alex mặc định. Giao diện so
        khoá này với `entry_id` trong kho để đánh dấu thẻ "Đang dùng"."""
        return "" if skin.is_default else digest_of_file(skin.skin_path)

    def remove_library_skin(self, entry_id: str) -> None:
        remove_from_library(self.paths.skins_dir, entry_id)

    def apply_library_skin(self, account: Account, entry_id: str) -> PlayerSkin:
        """Dùng một skin trong kho cho tài khoản: Microsoft thì upload lên Mojang (CHẠM MẠNG);
        loại khác thì chỉ đổi ảnh hiện trong launcher (Ely.by đổi thật ở ely.by)."""
        skin_entry = find_entry(self.paths.skins_dir, entry_id)
        if skin_entry is None:
            raise SkinError("skin này không còn trong thư viện")
        if account.account_kind == MICROSOFT:
            return self.upload_skin(account, skin_entry.skin_path, slim=skin_entry.slim)
        skins_dir = self.paths.skins_dir
        skins_dir.mkdir(parents=True, exist_ok=True)
        cache_key = _cache_key(account)
        (skins_dir / f"{cache_key}.png").write_bytes(skin_entry.skin_path.read_bytes())
        marker = skins_dir / f"{cache_key}.slim"
        if skin_entry.slim:
            marker.touch()
        else:
            marker.unlink(missing_ok=True)
        if account.account_kind == ELY:
            # Ely chỉ đổi skin thật qua web (upload.py); đây chỉ đổi ảnh trong launcher.
            # `refresh_skin` kế tiếp KHÔNG được âm thầm ghi đè lựa chọn này — đánh dấu để
            # `refresh_ely_skin` biết giữ lại cho tới khi server thật đồng bộ theo (JL-18 mục 5).
            (skins_dir / f"{cache_key}.local-override").touch()
        return self.describe_skin(account)

    def _collect(self, skin_path: Path, *, name: str, slim: bool, source: str) -> None:
        """Cất vào kho; kho lỗi (ảnh lạ, đĩa đầy) không được làm hỏng việc chính."""
        try:
            add_to_library(self.paths.skins_dir, skin_path, name=name, slim=slim, source=source)
        except SkinError:
            return

    def upload_skin(
        self,
        account: Account,
        skin_path: Path,
        *,
        slim: bool = False,
        client_id: str = "",
        cancel_token: CancelToken | None = None,
    ) -> PlayerSkin:
        """Upload skin mới lên Mojang (chỉ tài khoản Microsoft). CHẠM MẠNG.

        Làm mới vé trước (như luồng chơi) — vé hết hạn thì Mojang trả 401 thay vì launcher
        tự xin vé mới. Sau khi upload thành công, tải lại skin từ server để cập nhật cache.
        """
        if account.account_kind != MICROSOFT:
            raise AccountError("chỉ tài khoản Microsoft mới upload được skin lên Mojang")
        account = self._require_account(account.player_name, client_id, cancel_token)
        with self.make_http_client() as http_client:
            upload_skin_to_mojang(
                http_client, account.access_token, skin_path, slim=slim, endpoints=self.endpoints
            )
            skin = refresh_premium_skin(
                http_client, self.paths.skins_dir, account.player_uuid, endpoints=self.endpoints
            )
        self._collect(skin_path, name=skin_path.stem, slim=slim, source="upload")
        return skin


def _cache_key(account: Account) -> str:
    return skin_cache_key(account.account_kind, account.player_name, account.player_uuid)
