"""A separately published, verified server pack; reading its status never touches the network."""

import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.content.builtin_receipt import bundle_version
from nostalgia.content.mrpack import read_index
from nostalgia.errors import ContentError, IntegrityError
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.atomic_bytes import atomic_write
from nostalgia.storage.files import atomic_write_json, read_json
from nostalgia.storage.paths import DataPaths
from nostalgia.update.release import is_newer, parse_version

MAX_CHANNEL_BYTES = 65536
MAX_PACK_BYTES = 32 * 1024**2


@dataclass(frozen=True, slots=True)
class PackChannel:
    version_id: str
    game_version: str
    loader_version: str
    url: str
    sha256: str
    size: int


def parse_channel(document: JsonValue) -> PackChannel:
    fields = as_mapping(document)
    values = tuple(
        as_string(fields.get(key)) or ""
        for key in ("version", "minecraft", "fabric-loader", "url", "sha256")
    )
    version_id, game_version, loader_version, url, digest = values
    size = as_integer(fields.get("size")) or 0
    parts = urlsplit(url)
    if (
        fields.get("format") != 1
        or fields.get("preset") != "forgotten-worlds"
        or any(not value or len(value) > 2048 for value in values)
        or parse_version(version_id) is None
        or not re.fullmatch(r"[a-f0-9]{64}", digest)
        or not 0 < size <= MAX_PACK_BYTES
        or parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise ContentError("Nguồn cập nhật modpack không hợp lệ.")
    return PackChannel(version_id, game_version, loader_version, url, digest, size)


def channel_path(paths: DataPaths) -> Path:
    return paths.updates_dir / "modpacks" / "forgotten-worlds.json"


def cached_channel(paths: DataPaths) -> PackChannel | None:
    path = channel_path(paths)
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_size > MAX_CHANNEL_BYTES:
        raise ContentError("Bộ nhớ đệm cập nhật modpack không an toàn.")
    return parse_channel(read_json(path))


def refresh_channel(
    paths: DataPaths, http_client: HttpClient, url: str, cancel_token: CancelToken | None = None
) -> PackChannel:
    document = decode_json(
        http_client.fetch_bytes(url, max_bytes=MAX_CHANNEL_BYTES, cancel_token=cancel_token),
        what="Nguồn cập nhật modpack",
    )
    candidate = parse_channel(document)
    previous = cached_channel(paths)
    if previous is not None and is_newer(previous.version_id, candidate.version_id):
        raise ContentError("Nguồn cập nhật trả về modpack cũ hơn bản đã kiểm tra.")
    atomic_write_json(channel_path(paths), document)
    return candidate


def newer_channel(paths: DataPaths, bundled_pack: Path) -> PackChannel | None:
    channel = cached_channel(paths)
    if channel is None or not is_newer(channel.version_id, bundle_version(bundled_pack)):
        return None
    with zipfile.ZipFile(bundled_pack) as archive:
        fields = as_mapping(decode_json(archive.read("modrinth.index.json"), what="Modpack"))
    dependencies = as_mapping(fields.get("dependencies"))
    if (channel.game_version, channel.loader_version) != (
        dependencies.get("minecraft"),
        dependencies.get("fabric-loader"),
    ):
        raise ContentError("Modpack trực tuyến không khớp Minecraft và Fabric của gói này.")
    return channel


def channel_pack(
    paths: DataPaths,
    channel: PackChannel,
    http_client: HttpClient,
    *,
    allowed_hosts: tuple[str, ...],
    cancel_token: CancelToken | None = None,
) -> Path:
    path = channel_path(paths).parent / (channel.sha256 + ".mrpack")
    if path.is_symlink():
        raise ContentError("File cập nhật modpack là symlink.")
    payload = path.read_bytes() if path.exists() and path.stat().st_size == channel.size else b""
    if hashlib.sha256(payload).hexdigest() != channel.sha256:
        payload = http_client.fetch_bytes(
            channel.url, max_bytes=channel.size, cancel_token=cancel_token
        )
    if len(payload) != channel.size or hashlib.sha256(payload).hexdigest() != channel.sha256:
        raise IntegrityError(
            "File modpack cập nhật không khớp mã kiểm tra; bản chơi được giữ nguyên."
        )
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    atomic_write(path, payload)
    index = read_index(path, allowed_hosts=allowed_hosts)
    if (bundle_version(path), index.game_version, index.loader_kind, index.loader_version) != (
        channel.version_id,
        channel.game_version,
        "fabric",
        channel.loader_version,
    ):
        raise ContentError("Nội dung modpack không khớp thông tin cập nhật.")
    return path
