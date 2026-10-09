"""Hồ sơ công khai cho bạn bè; skin và modpack chỉ chia sẻ khi chủ hồ sơ chọn."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FavoritePack:
    title: str
    game_version: str


@dataclass(frozen=True, slots=True)
class ProfileDraft:
    bio: str = ""
    avatar_mode: str = "google"
    skin_png: str = ""
    slim: bool = False
    favorite_packs: tuple[FavoritePack, ...] = ()
    decor: str = "none"
    avatar_png: str = ""


@dataclass(frozen=True, slots=True)
class SocialProfile:
    account_id: str
    name: str
    online: bool
    avatar_url: str
    details: ProfileDraft
    badge: str = ""
    accent: str = ""
    owned_cosmetics: tuple[str, ...] = ()
