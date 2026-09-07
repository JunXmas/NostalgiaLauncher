"""Lấy skin/cape về đĩa: premium qua sessionserver Mojang (công khai, theo UUID), Ely.by theo tên.

Cache ở `skins_dir/<khoá>.png`; tải lại mỗi lần gọi `refresh` (file nhỏ, vài KB), lỗi mạng thì
dùng cache cũ, không có cache thì Steve/Alex. Không bao giờ ném lỗi ra giao diện vì skin.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from nostalgia.errors import NostalgiaError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import fetch_json
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints
from nostalgia.skin.defaults import default_skin
from nostalgia.skin.model import PlayerSkin
from nostalgia.storage.files import ensure_dir

logger = logging.getLogger(__name__)

MAX_TEXTURE_BYTES = 512 * 1024


def parse_session_profile(document: JsonValue) -> tuple[str, str, bool]:
    """(skin_url, cape_url, slim) từ hồ sơ sessionserver; thiếu thì chuỗi rỗng. Thuần."""
    for property_value in as_list(as_mapping(document).get("properties")):
        entry_map = as_mapping(property_value)
        if as_string(entry_map.get("name")) != "textures":
            continue
        decoded = json.loads(base64.b64decode(as_string(entry_map.get("value")) or ""))
        textures = as_mapping(as_mapping(decoded).get("textures"))
        skin = as_mapping(textures.get("SKIN"))
        cape = as_mapping(textures.get("CAPE"))
        slim = as_string(as_mapping(skin.get("metadata")).get("model")) == "slim"
        return as_string(skin.get("url")) or "", as_string(cape.get("url")) or "", slim
    return "", "", False


def cached_skin(skins_dir: Path, cache_key: str, player_uuid: str) -> PlayerSkin:
    """Đọc đĩa, không chạm mạng. `.slim` ghi cạnh file skin để khỏi phải tải lại hồ sơ."""
    skin_path = skins_dir / f"{cache_key}.png"
    if not skin_path.is_file():
        return default_skin(player_uuid)
    cape_path = skins_dir / f"{cache_key}.cape.png"
    slim = (skins_dir / f"{cache_key}.slim").is_file()
    return PlayerSkin(skin_path, slim, cape_path if cape_path.is_file() else None, False)


def refresh_premium_skin(
    http_client: HttpClient,
    skins_dir: Path,
    player_uuid: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
) -> PlayerSkin:
    """CHẠM MẠNG. Hồ sơ công khai theo UUID → tải skin (và cape nếu có) về cache."""
    undashed = player_uuid.replace("-", "")
    try:
        document = fetch_json(
            http_client, f"{endpoints.mojang_session_profile}/{undashed}", what="hồ sơ skin"
        )
        skin_url, cape_url, slim = parse_session_profile(document)
        if not skin_url:
            return cached_skin(skins_dir, undashed, player_uuid)
        _store(http_client, skins_dir, undashed, skin_url, cape_url, slim)
    except (NostalgiaError, ValueError, OSError) as exc:
        logger.warning("không tải được skin premium cho %s: %s", undashed, exc)
    return cached_skin(skins_dir, undashed, player_uuid)


def refresh_ely_skin(
    http_client: HttpClient,
    skins_dir: Path,
    player_name: str,
    player_uuid: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
) -> PlayerSkin:
    """CHẠM MẠNG. Ely.by phục vụ skin theo tên; slim không biết trước nên đọc từ ảnh sau."""
    cache_key = f"ely-{player_name.lower()}"
    try:
        _store(
            http_client,
            skins_dir,
            cache_key,
            f"{endpoints.ely_skins}/{player_name}.png",
            f"{endpoints.ely_capes}/{player_name}.png",
            slim=False,
        )
    except (NostalgiaError, OSError) as exc:
        logger.warning("không tải được skin Ely.by cho %s: %s", player_name, exc)
    return cached_skin(skins_dir, cache_key, player_uuid)


def _upgrade_to_https(url: str) -> str:
    """Mojang sessionserver trả skin URL bằng http. Host chấp nhận https — dùng nó."""
    if url.startswith("http://textures.minecraft.net/"):
        return "https" + url[4:]
    return url


def _store(
    http_client: HttpClient,
    skins_dir: Path,
    cache_key: str,
    skin_url: str,
    cape_url: str,
    slim: bool,
) -> None:
    ensure_dir(skins_dir)
    skin_bytes = http_client.fetch_bytes(_upgrade_to_https(skin_url), max_bytes=MAX_TEXTURE_BYTES)
    (skins_dir / f"{cache_key}.png").write_bytes(skin_bytes)
    slim_marker = skins_dir / f"{cache_key}.slim"
    if slim:
        slim_marker.touch()
    else:
        slim_marker.unlink(missing_ok=True)
    cape_path = skins_dir / f"{cache_key}.cape.png"
    if cape_url:
        try:
            url = _upgrade_to_https(cape_url)
            cape_bytes = http_client.fetch_bytes(url, max_bytes=MAX_TEXTURE_BYTES)
            cape_path.write_bytes(cape_bytes)
        except NostalgiaError:
            cape_path.unlink(missing_ok=True)
    else:
        cape_path.unlink(missing_ok=True)
