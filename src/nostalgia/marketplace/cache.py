"""Cache theo băm nội dung; tải model không cấp quyền trang bị."""

import hashlib
import re
import tempfile
from pathlib import Path

from nostalgia.errors import SocialError
from nostalgia.marketplace.asset import parse_asset
from nostalgia.model.cosmetic import CosmeticAsset
from nostalgia.net.http import HttpClient
from nostalgia.storage.files import ensure_dir


def sync_cosmetic_asset(
    http_client: HttpClient, base_url: str, digest: str, cache_dir: Path
) -> CosmeticAsset:
    if not re.fullmatch("[a-f0-9]{64}", digest):
        raise SocialError("Invalid cosmetic hash")
    path = cache_dir / (digest + ".json")
    payload = path.read_bytes() if path.is_file() and path.stat().st_size <= 1_000_000 else b""
    if hashlib.sha256(payload).hexdigest() != digest:
        payload = http_client.fetch_bytes(
            base_url + "/v1/marketplace/assets/" + digest, max_bytes=1_000_000
        )
        if hashlib.sha256(payload).hexdigest() != digest:
            raise SocialError("Cosmetic asset hash mismatch")
        cosmetic = parse_asset(payload)
        ensure_dir(cache_dir)
        with tempfile.TemporaryDirectory(dir=cache_dir, prefix="stage-") as temporary:
            temporary_path = Path(temporary) / "asset.json"
            temporary_path.write_bytes(payload)
            temporary_path.replace(path)
    else:
        cosmetic = parse_asset(payload)
    path.touch()
    # Giữ file hiện tại; cache cũ có thể tải lại, không phải inventory.
    cached = sorted(cache_dir.glob("*.json"), key=lambda candidate: candidate.stat().st_mtime)
    total = sum(candidate.stat().st_size for candidate in cached)
    for candidate in cached:
        if total <= 512 * 1024 * 1024:
            break
        if candidate != path:
            total -= candidate.stat().st_size
            candidate.unlink(missing_ok=True)
    return cosmetic
