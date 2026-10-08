"""URL ảnh Google và PNG nhỏ; từ chối file/URL tùy ý từ mạng."""

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.social.cosmetic import is_cosmetic_id
from nostalgia.social.parse import accent, badge, identifier, rows, text
from nostalgia.social.profile_image import image_url, png
from nostalgia.social.profile_model import FavoritePack, ProfileDraft, SocialProfile


def parse_profile(document: JsonValue) -> SocialProfile:
    fields = as_mapping(document)
    avatar_mode = as_string(fields.get("avatar_mode")) or "google"
    decor = as_string(fields.get("decor")) or "none"
    if avatar_mode not in ("google", "skin", "initials") or not is_cosmetic_id(decor):
        raise SocialError("Trang trí hồ sơ không hợp lệ.")
    skin_png = png(fields.get("skin_png"))
    return SocialProfile(
        identifier(text(fields.get("account_id"), 96)),
        text(fields.get("name")),
        fields.get("online") is True,
        image_url(fields.get("avatar_url")),
        ProfileDraft(
            text(fields.get("bio"), 160) if fields.get("bio") else "",
            avatar_mode,
            skin_png,
            fields.get("slim") is True,
            tuple(
                FavoritePack(
                    text(as_mapping(p).get("title"), 100),
                    text(as_mapping(p).get("game_version"), 96),
                )
                for p in rows(fields.get("favorite_packs", []), 3)
            ),
            decor,
            png(fields.get("avatar_png"), 8, 512),
        ),
        badge(fields.get("badge")),
        accent(fields.get("accent")),
    )
