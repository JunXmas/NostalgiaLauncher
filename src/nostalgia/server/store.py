"""Owned server directories. Unknown keys survive; symlinks never escape the store."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import asdict
from pathlib import Path

from nostalgia.errors import ServerError
from nostalgia.server.model import DedicatedServer, server_engine
from nostalgia.storage.atomic_bytes import atomic_write
from nostalgia.storage.files import resolve_within


def owned_path(root_dir: Path, relative_path: str) -> Path:
    path = resolve_within(root_dir, relative_path)
    for parent in (root_dir, *reversed(path.relative_to(root_dir).parents), path):
        candidate = parent if parent in (root_dir, path) else root_dir / parent
        if candidate.is_symlink():
            raise ServerError("Không đọc hoặc ghi cấu hình qua liên kết ngoài thư mục server.")
    if not path.resolve().is_relative_to(root_dir.resolve()):
        raise ServerError("Đường dẫn nằm ngoài thư mục server.")
    return path


class ServerStore:
    def __init__(self, data_dir: Path) -> None:
        self.root_dir = data_dir / "servers"

    def directory(self, server_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", server_id):
            raise ServerError("Mã server không hợp lệ.")
        return owned_path(self.root_dir, server_id)

    def list_servers(self) -> tuple[DedicatedServer, ...]:
        if not self.root_dir.exists():
            return ()
        if self.root_dir.is_symlink():
            raise ServerError("Thư mục server không được là liên kết.")
        return tuple(
            self.load(child.name)
            for child in sorted(self.root_dir.iterdir())
            if not child.name.startswith(".")
            and child.is_dir()
            and (child / "nostalgia-server.json").is_file()
        )

    def load(self, server_id: str) -> DedicatedServer:
        path = owned_path(self.directory(server_id), "nostalgia-server.json")
        try:
            if path.stat().st_size > 16_384:
                raise ServerError("Metadata server vượt giới hạn.")
            fields = json.loads(path.read_text(encoding="utf-8"))
            server = DedicatedServer(**fields)
            if server.server_id != server_id or not re.fullmatch(
                r"[a-f0-9]{64}", server.jar_sha256
            ):
                raise ValueError("identity/digest")
            server_engine(server.engine_id)
            return server
        except (OSError, ValueError, TypeError) as error:
            raise ServerError("Không đọc được metadata server.") from error

    def save(self, server: DedicatedServer) -> None:
        directory = self.directory(server.server_id)
        directory.mkdir(parents=True, exist_ok=True)
        atomic_write(
            owned_path(directory, "nostalgia-server.json"), json.dumps(asdict(server)).encode()
        )

    def trash(self, server_id: str) -> Path:
        directory = self.directory(server_id)
        trash_dir = owned_path(self.root_dir, ".trash")
        trash_dir.mkdir(parents=True, exist_ok=True)
        destination = trash_dir / (server_id + "-" + uuid.uuid4().hex)
        directory.rename(destination)
        return destination


def jar_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
