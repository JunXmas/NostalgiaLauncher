"""Icon chia sẻ chỉ từ CDN đã biết hoặc PNG nhỏ; không nhận URL nội bộ/file/SVG."""

import base64
import json
import struct
import tomllib
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.errors import ContentError
from nostalgia.modcheck.archive import read_member
from nostalgia.model.json_value import as_list, as_mapping, as_string


def safe_sync_icon(text: str) -> str:
    if len(text) > 22000:
        return ""
    if text.startswith("data:image/png;base64,"):
        try:
            payload = base64.b64decode(text.split(",", 1)[1], validate=True)
            return text if small_png(payload) else ""
        except ValueError:
            return ""
    try:
        address = urlsplit(text)
        return (
            text
            if (
                len(text) <= 2048
                and address.scheme == "https"
                and not address.username
                and not address.password
                and address.port in (None, 443)
                and address.hostname
                in ("cdn.modrinth.com", "media.forgecdn.net", "mediafilez.forgecdn.net")
            )
            else ""
        )
    except ValueError:
        return ""


def small_png(payload: bytes) -> bool:
    if not 33 <= len(payload) <= 16384 or payload[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        return False
    width, height = struct.unpack(">II", payload[16:24])
    return bool(0 < width <= 256 and 0 < height <= 256)


def archive_icon(path: Path) -> str:
    try:
        if path.is_symlink() or not path.is_file():
            return ""
        with zipfile.ZipFile(path) as archive:
            candidates = ["pack.png", "icon.png", "logo.png"]
            for member in ("fabric.mod.json", "quilt.mod.json", "mcmod.info"):
                if payload := read_member(archive, member):
                    fields = json.loads(payload)
                    fields = (
                        as_mapping(as_list(fields)[0])
                        if isinstance(fields, list) and fields
                        else as_mapping(fields)
                    )
                    if member == "quilt.mod.json":
                        fields = as_mapping(as_mapping(fields.get("quilt_loader")).get("metadata"))
                    icon = fields.get("icon", fields.get("logoFile"))
                    if isinstance(icon, dict):
                        icon = next(iter(icon.values()), "")
                    if isinstance(icon, str):
                        candidates.insert(0, icon)
            for member in ("META-INF/mods.toml", "META-INF/neoforge.mods.toml"):
                if payload := read_member(archive, member):
                    fields = as_mapping(tomllib.loads(payload.decode("utf-8")))
                    for mod in as_list(fields.get("mods")):
                        if logo := as_string(as_mapping(mod).get("logoFile")):
                            candidates.insert(0, logo)
            for candidate in candidates:
                try:
                    payload = read_member(archive, candidate, 16384)
                    if small_png(payload):
                        return "data:image/png;base64," + base64.b64encode(payload).decode("ascii")
                except ContentError:
                    continue
    except (OSError, ValueError, TypeError, UnicodeError, zipfile.BadZipFile, ContentError):
        pass
    return ""


def sync_title(text: str) -> str:
    return "".join(char for char in text if ord(char) >= 32 and char not in "<>")[:160]
