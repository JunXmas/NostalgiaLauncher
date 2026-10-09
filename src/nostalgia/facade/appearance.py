"""Lưu skin đã xem trước và cache texture cape cho renderer cục bộ."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from nostalgia.account.model import ELY, MICROSOFT, Account
from nostalgia.facade.skins import SkinOperations
from nostalgia.skin.capes import OwnedCape
from nostalgia.skin.library import digest_of_file
from nostalgia.skin.model import PlayerSkin
from nostalgia.skin.textures import MAX_TEXTURE_BYTES, _upgrade_to_https, skin_cache_key


@dataclass(frozen=True, slots=True)
class AppearanceOperations(SkinOperations):
    def cape_digest(self, skin: PlayerSkin) -> str:
        return digest_of_file(skin.cape_path) if skin.cape_path else ""

    def save_skin_selection(self, account: Account, skin_path: Path, *, slim: bool) -> PlayerSkin:
        """Chỉ gọi khi người chơi bấm Lưu; không đổi tài khoản đang chọn ở giữa tác vụ."""
        skin_entry = self.import_skin(skin_path, slim=slim)
        if account.account_kind == MICROSOFT:
            return self.upload_skin(account, skin_entry.skin_path, slim=slim)
        if account.account_kind == ELY:
            return self.upload_skin_to_ely(account, skin_entry.skin_path, slim=slim)
        self.apply_library_skin(account, skin_entry.entry_id)
        marker = self.paths.skins_dir / (
            skin_cache_key(account.account_kind, account.player_name, account.player_uuid) + ".slim"
        )
        if slim:
            marker.touch()
        else:
            marker.unlink(missing_ok=True)
        return self.describe_skin(account)

    def cache_cape_texture(self, cape: OwnedCape) -> Path | None:
        """Tải texture công khai từ cape sở hữu; cache có giới hạn kích thước file."""
        if not cape.texture_url:
            return None
        directory = self.paths.data_dir / "cache" / "cape-textures"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (hashlib.sha256(cape.texture_url.encode()).hexdigest() + ".png")
        if not path.is_file():
            with self.make_http_client() as http_client:
                content = http_client.fetch_bytes(
                    _upgrade_to_https(cape.texture_url), max_bytes=MAX_TEXTURE_BYTES
                )
            path.write_bytes(content)
        return path
