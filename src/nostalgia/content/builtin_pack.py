"""Modpack client ghim sẵn theo bộ mod của server Forgotten Worlds."""

from importlib.resources import files
from pathlib import Path

FORGOTTEN_WORLDS = "forgotten-worlds"
FORGOTTEN_GAME_VERSIONS = ("1.21.11",)


def load_forgotten_worlds_pack() -> Path:
    """Đường dẫn gói đi cùng launcher; không cần tài khoản hay API key của hosting."""
    resource = files("nostalgia.content") / "packs" / "forgotten-worlds-1.21.11.mrpack"
    return Path(str(resource))
