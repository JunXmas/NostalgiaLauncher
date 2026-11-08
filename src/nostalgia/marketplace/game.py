"""Khóa game tạm chỉ ở bộ nhớ launcher; bootstrap trên đĩa chỉ có port/nonce."""

import json
import secrets
import threading
from pathlib import Path

from nostalgia.model.json_value import as_mapping
from nostalgia.model.marketplace import GameCosmeticSession
from nostalgia.net.cosmetic_loopback import CosmeticLoopback
from nostalgia.net.session_proof import public_key
from nostalgia.storage.files import atomic_write_json


class CosmeticGameBridge:
    def __init__(self, game_dir: Path, api_url: str) -> None:
        self._seed = secrets.token_hex(32)
        self.public_key = public_key(self._seed)
        self._api_url = api_url.rstrip("/")
        self._session: GameCosmeticSession | None = None
        self._lock = threading.Lock()
        self._server = CosmeticLoopback(self._read)
        self._path = game_dir / "config/nostalgia-cosmetics.json"
        self._closed = False

    def _publish(self) -> None:
        atomic_write_json(
            self._path,
            {
                "schema_version": 1,
                "port": self._server.bootstrap.port,
                "nonce": self._server.bootstrap.nonce,
            },
            private=True,
        )

    def update(self, game_session: GameCosmeticSession) -> None:
        if game_session.public_key != self.public_key:
            raise ValueError("Cosmetic game session key mismatch")
        with self._lock:
            if self._closed:
                return
            self._publish()
            self._session = game_session

    def _read(self) -> bytes:
        with self._lock:
            game_session = self._session
            seed = self._seed
        if game_session is None:
            return b'{"ready":false}'
        return json.dumps(
            {
                "ready": True,
                "api_url": self._api_url,
                "capability": game_session.capability,
                "public_key": game_session.public_key,
                "private_seed": seed,
                "expires_at": game_session.expires_at,
                "loadout": [
                    {"slot": slot.slot, "asset_hash": slot.asset_hash}
                    for slot in game_session.loadout
                ],
            }
        ).encode()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._seed = ""
            self._session = None
        self._server.close()
        try:
            document = as_mapping(json.loads(self._path.read_bytes()))
            if document.get("nonce") == self._server.bootstrap.nonce:
                self._path.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError):
            pass
