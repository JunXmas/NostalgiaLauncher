"""IPC loopback thật: không token Google, chỉ publish bootstrap sau khi sẵn sàng."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from nostalgia.marketplace.game import CosmeticGameBridge
from nostalgia.model.marketplace import GameCosmeticSession


def test_bootstrap_published_only_when_ready_and_late_update_cannot_resurrect(
    tmp_path: Path,
) -> None:
    game = CosmeticGameBridge(tmp_path, "https://accounts.test/")
    path = tmp_path / "config/nostalgia-cosmetics.json"
    assert not path.exists()
    game_session = GameCosmeticSession("a" * 64, game.public_key, 4_000_000_000, ())
    try:
        game.update(game_session)
        bootstrap = json.loads(path.read_bytes())
        assert set(bootstrap) == {"schema_version", "port", "nonce"}
        if os.name != "nt":
            assert path.stat().st_mode & 0o077 == 0
        endpoint = f"http://127.0.0.1:{bootstrap['port']}/cosmetic/{bootstrap['nonce']}"
        with urlopen(endpoint, timeout=2) as response:
            value = json.load(response)
        assert value["capability"] == "a" * 64
        assert value["api_url"] == "https://accounts.test"
        assert not {"access_token", "email", "account_id", "wallet"} & value.keys()
        for request in (
            Request(endpoint, headers={"Origin": "https://hostile.test"}),
            Request(endpoint + "wrong"),
            Request(endpoint, data=b"{}"),
        ):
            with pytest.raises(HTTPError) as error:
                urlopen(request, timeout=2)
            assert error.value.code in (403, 501)
    finally:
        game.close()
    assert not path.exists()
    game.update(game_session)
    assert not path.exists()
