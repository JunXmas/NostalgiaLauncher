"""Small typed server.properties editor; retain vendor/advanced keys and comments."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import ServerError
from nostalgia.server.store import owned_path
from nostalgia.storage.atomic_bytes import atomic_write

DEFAULTS = {
    "server-port": "25565",
    "max-players": "20",
    "view-distance": "10",
    "simulation-distance": "8",
    "spawn-protection": "16",
    "difficulty": "normal",
    "gamemode": "survival",
    "pvp": "true",
    "white-list": "false",
    "online-mode": "true",
    "motd": "A Nostalgia server",
}
BOUNDS = {
    "server-port": (1024, 65535),
    "max-players": (1, 1000),
    "view-distance": (2, 32),
    "simulation-distance": (2, 32),
    "spawn-protection": (0, 10000),
}
CHOICES = {
    "difficulty": ("peaceful", "easy", "normal", "hard"),
    "gamemode": ("survival", "creative", "adventure", "spectator"),
    "pvp": ("true", "false"),
    "white-list": ("true", "false"),
    "online-mode": ("true", "false"),
}


@dataclass(frozen=True, slots=True)
class ServerProperties:
    values: tuple[tuple[str, str], ...]
    eula_accepted: bool = False


def _read(directory: Path, relative_path: str) -> str:
    path = owned_path(directory, relative_path)
    if not path.exists():
        return ""
    if path.stat().st_size > 256_000:
        raise ServerError("Cấu hình quá lớn để sửa trong launcher.")
    return path.read_text(encoding="utf-8")


def _key(line: str) -> str:
    if line.lstrip().startswith(("#", "!")):
        return ""
    return re.split(r"[=:\s]", line.lstrip(), maxsplit=1)[0]


def _unescape(value: str) -> str:
    def decode(match: re.Match[str]) -> str:
        escaped = match[1]
        if escaped.startswith("u") and len(escaped) == 5:
            return chr(int(escaped[1:], 16))
        return {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}.get(escaped, escaped)

    return re.sub(r"\\(u[0-9a-fA-F]{4}|.)", decode, value)


def load_properties(directory: Path) -> ServerProperties:
    values = DEFAULTS.copy()
    for line in _read(directory, "server.properties").splitlines():
        property_key = _key(line)
        if property_key in values:
            values[property_key] = _unescape(re.sub(r"^[^=: \t]+\s*[=:]?\s*", "", line.lstrip()))
    accepted = any(
        re.fullmatch(r"eula\s*=\s*true\s*", line)
        for line in _read(directory, "eula.txt").splitlines()
    )
    return ServerProperties(tuple(values.items()), accepted)


def save_properties(directory: Path, properties: ServerProperties) -> None:
    values = dict(properties.values)
    if set(values) != set(DEFAULTS):
        raise ServerError("Thiếu hoặc thừa trường cấu hình server.")
    for property_key, value in values.items():
        if not isinstance(value, str) or any(ord(c) < 32 for c in value) or len(value) > 240:
            raise ServerError("Giá trị cấu hình phải là một dòng, tối đa 240 ký tự.")
        if property_key in BOUNDS:
            lower, upper = BOUNDS[property_key]
            if not value.isdigit() or not lower <= int(value) <= upper:
                raise ServerError(f"{property_key} phải nằm trong khoảng {lower}-{upper}.")
        if property_key in CHOICES and value not in CHOICES[property_key]:
            raise ServerError(f"{property_key} không hợp lệ.")
    lines = _read(directory, "server.properties").splitlines()
    updated: list[str] = []
    remaining = values.copy()
    for line in lines:
        property_key = _key(line)
        if property_key not in values:
            updated.append(line)
        elif property_key in remaining:
            value = remaining.pop(property_key).replace("\\", "\\\\")
            updated.append(property_key + "=" + value)
    updated.extend(
        property_key + "=" + value.replace("\\", "\\\\")
        for property_key, value in remaining.items()
    )
    atomic_write(owned_path(directory, "server.properties"), ("\n".join(updated) + "\n").encode())
    atomic_write(
        owned_path(directory, "eula.txt"),
        ("eula=" + str(properties.eula_accepted).lower() + "\n").encode(),
    )


def config_files(directory: Path) -> tuple[str, ...]:
    candidates: list[str] = []
    for folder, directories, files in os.walk(directory, followlinks=False):
        folder_path = Path(folder)
        directories[:] = sorted(
            d
            for d in directories
            if not d.startswith(".")
            and d not in ("libraries", "logs", "cache", "versions", "worlds")
            and not (folder_path / d / "level.dat").is_file()
            and not (folder_path / d).is_symlink()
        )
        for file_name in sorted(files):
            path = folder_path / file_name
            if (
                path.suffix in (".yml", ".yaml", ".toml", ".json", ".properties")
                and not path.is_symlink()
                and file_name != "nostalgia-server.json"
            ):
                candidates.append(path.relative_to(directory).as_posix())
                if len(candidates) == 100:
                    return tuple(candidates)
    return tuple(candidates)


def read_config(directory: Path, relative_path: str) -> str:
    if relative_path not in config_files(directory):
        raise ServerError("Chỉ sửa file cấu hình có sẵn trong thư mục server.")
    return _read(directory, relative_path)


def save_config(directory: Path, relative_path: str, text: str) -> None:
    read_config(directory, relative_path)
    if len(text.encode()) > 256_000 or "\x00" in text:
        raise ServerError("Cấu hình vượt giới hạn.")
    atomic_write(owned_path(directory, relative_path), text.encode())
