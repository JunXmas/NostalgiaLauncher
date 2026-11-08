"""Cache model không là quyền sở hữu; dữ liệu hỏng không đi đến renderer."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from market_fixture import ASSET_HASH, ASSET_PAYLOAD
from nostalgia.errors import SocialError
from nostalgia.marketplace.asset import parse_asset
from nostalgia.marketplace.cache import sync_cosmetic_asset
from nostalgia.net.http import HttpClient


class AssetTransport:
    def __init__(self, payload: bytes = ASSET_PAYLOAD) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def fetch_bytes(self, url: str, **_kwargs: Any) -> bytes:
        self.calls.append(url)
        return self.payload


def test_model_cached_once_and_corruption_repaired(tmp_path: Path) -> None:
    transport = AssetTransport()
    http_client = cast(HttpClient, transport)
    assert sync_cosmetic_asset(http_client, "https://test.invalid", ASSET_HASH, tmp_path).parts
    sync_cosmetic_asset(http_client, "https://test.invalid", ASSET_HASH, tmp_path)
    assert len(transport.calls) == 1
    (tmp_path / (ASSET_HASH + ".json")).write_bytes(b"corrupt")
    sync_cosmetic_asset(http_client, "https://test.invalid", ASSET_HASH, tmp_path)
    assert len(transport.calls) == 2


def test_bad_hash_never_cached_or_loaded(tmp_path: Path) -> None:
    transport = cast(HttpClient, AssetTransport(b"bad"))
    with pytest.raises(SocialError):
        sync_cosmetic_asset(transport, "https://test.invalid", ASSET_HASH, tmp_path)
    assert not tuple(tmp_path.iterdir())


@pytest.mark.parametrize("change", ["cycle", "script", "giant", "nan", "external"])
def test_invalid_model_rejected(change: str) -> None:
    document = json.loads(ASSET_PAYLOAD)
    node = document["parts"][0]["model"]["nodes"][0]
    if change == "cycle":
        node["parent"] = 0
    elif change == "script":
        document["script"] = "evil"
    elif change == "giant":
        node["vertices"] *= 2000
    elif change == "nan":
        node["vertices"][0] = float("nan")
    else:
        document["parts"][0]["model"]["texture"] = "https://evil.invalid"
    with pytest.raises(SocialError):
        parse_asset(json.dumps(document).encode())
