"""Official Minecraft release validation and numeric ordering."""

import re

from nostalgia.errors import ServerError

VERSION_PATTERN = r"[0-9]+(?:\.[0-9]+){1,2}"


def validate_game_version(value: str) -> str:
    if not re.fullmatch(VERSION_PATTERN, value):
        raise ServerError("Chỉ chọn phiên bản Minecraft phát hành chính thức.")
    return value


def sort_game_versions(values: list[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {v for v in values if re.fullmatch(VERSION_PATTERN, v)},
            key=lambda v: tuple(int(part) for part in v.split(".")),
            reverse=True,
        )
    )
