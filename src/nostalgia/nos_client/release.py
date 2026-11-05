"""Chọn gói Nos theo Minecraft từ các bản phát hành ổn định, kể cả bản không gắn Latest."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from nostalgia.errors import DataFileError, NetworkError
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.nos_client.compatibility import SUPPORTED_GAME_VERSIONS
from nostalgia.operations.cancellation import CancelToken
from nostalgia.update.release import parse_sha256sums

logger = logging.getLogger(__name__)
GITHUB_API_BASE = "https://api.github.com"
REPOSITORY = "JunXmas/nos-client"
MOD_JAR_PREFIX = "nos-client-"
MAX_JAR_BYTES = 64 * 1024 * 1024
_JAR_NAME = re.compile(r"nos-client-(\d+\.\d+\.\d+)(?:\+mc(\d+(?:\.\d+){1,2}))?\.jar")


@dataclass(frozen=True, slots=True)
class ModRelease:
    tag: str
    download_url: str
    file_name: str
    size: int
    sha256: str | None
    checksums_url: str = ""


def resolve_artifact_game_version(file_name: str) -> str | None:
    """Gói trước khi tách nhánh Minecraft chỉ dành cho 1.21.11."""
    match = _JAR_NAME.fullmatch(file_name)
    return (match.group(2) or "1.21.11") if match else None


def resolve_mod_version(file_name: str) -> str:
    return file_name.removeprefix(MOD_JAR_PREFIX).removesuffix(".jar")


def resolve_mod_version_key(file_name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in resolve_mod_version(file_name).split("+")[0].split("."))


def parse_mod_releases(document: JsonValue, game_version: str) -> tuple[ModRelease, ...]:
    if game_version not in SUPPORTED_GAME_VERSIONS:
        return ()
    releases = []
    for document_release in as_list(document):
        release = as_mapping(document_release)
        if release.get("draft") is not False or release.get("prerelease") is not False:
            continue
        tag = as_string(release.get("tag_name"))
        if not tag:
            continue
        release_assets = tuple(as_mapping(value) for value in as_list(release.get("assets")))
        checksums_url = next(
            (
                as_string(value.get("browser_download_url")) or ""
                for value in release_assets
                if value.get("name") == "SHA256SUMS"
            ),
            "",
        )
        for release_asset in release_assets:
            file_name = as_string(release_asset.get("name")) or ""
            if resolve_artifact_game_version(file_name) != game_version:
                continue
            url = as_string(release_asset.get("browser_download_url")) or ""
            size = as_integer(release_asset.get("size"))
            try:
                parts = urlsplit(url)
            except ValueError:
                continue
            if (
                parts.scheme != "https"
                or not parts.netloc
                or size is None
                or not 0 < size <= MAX_JAR_BYTES
            ):
                continue
            digest = as_string(release_asset.get("digest"))
            sha256 = None
            if digest is not None:
                if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
                    continue
                sha256 = digest.removeprefix("sha256:").lower()
            releases.append(ModRelease(tag, url, file_name, size, sha256, checksums_url))
    return tuple(
        sorted(releases, key=lambda value: resolve_mod_version_key(value.file_name), reverse=True)
    )


def fetch_compatible_release(
    http_client: HttpClient, game_version: str, *, cancel_token: CancelToken | None = None
) -> ModRelease | None:
    """Đọc tối đa 100 release và so phiên bản số, không dựa vào thứ tự file hoặc ngày tạo tag."""
    if game_version not in SUPPORTED_GAME_VERSIONS:
        return None
    candidates: list[ModRelease] = []
    for page in range(1, 6):
        url = f"{GITHUB_API_BASE}/repos/{REPOSITORY}/releases?per_page=20&page={page}"
        try:
            document = decode_json(
                http_client.fetch_bytes(url, max_bytes=1024 * 1024, cancel_token=cancel_token),
                what=url,
            )
        except (NetworkError, DataFileError):
            logger.warning("Could not fetch Nos Client releases for Minecraft %s", game_version)
            return None
        candidates.extend(parse_mod_releases(document, game_version))
        if not isinstance(document, list) or len(document) < 20:
            break
    return max(candidates, key=lambda value: resolve_mod_version_key(value.file_name), default=None)


def fetch_release_sha256(
    http_client: HttpClient, release: ModRelease, *, cancel_token: CancelToken | None = None
) -> str | None:
    """Digest GitHub được ưu tiên; release cũ cần SHA256SUMS thay thế, không tải jar mù."""
    if release.sha256:
        return release.sha256
    if not release.checksums_url.startswith("https://"):
        return None
    text = http_client.fetch_bytes(
        release.checksums_url, max_bytes=64 * 1024, cancel_token=cancel_token
    ).decode("utf-8")
    digest = parse_sha256sums(text).get(release.file_name, "")
    return digest if re.fullmatch(r"[0-9a-f]{64}", digest) else None
