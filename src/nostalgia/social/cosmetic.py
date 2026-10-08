"""Danh mục cosmetic đóng gói; dữ liệu hiển thị không cấp quyền Plus."""

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import Literal, cast

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue, as_mapping


@dataclass(frozen=True, slots=True)
class CosmeticSet:
    key: str
    name: str
    artwork: str
    tint: str
    accent: str
    description: str
    state: Literal["active", "retired", "disabled"]


@dataclass(frozen=True, slots=True)
class CosmeticCollection:
    revision: int
    sets: tuple[CosmeticSet, ...]


def is_cosmetic_id(value: str) -> bool:
    """Cho phép mã mới từ máy chủ; không biến mã thành URL/đường dẫn."""
    return bool(re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value))


def parse_cosmetic_collection(document: JsonValue) -> CosmeticCollection:
    fields = as_mapping(document)
    revision, candidates = fields.get("revision"), fields.get("items")
    if (
        fields.get("schema") != 1
        or isinstance(fields.get("schema"), bool)
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < 1
        or not isinstance(candidates, list)
        or len(candidates) > 128
    ):
        raise SocialError("Invalid cosmetic collection")
    cosmetics = []
    for candidate in candidates:
        values = as_mapping(candidate)
        required = {"key", "name", "artwork", "tint", "accent", "description", "state"}
        if set(values) != required or any(not isinstance(v, str) for v in values.values()):
            raise SocialError("Invalid cosmetic definition")
        strings = cast(dict[str, str], values)
        if (
            not is_cosmetic_id(strings["key"])
            or strings["key"] == "none"
            or not is_cosmetic_id(strings["artwork"])
            or not 1 <= len(strings["name"].strip()) <= 60
            or len(strings["description"]) > 160
            or not re.fullmatch(r"#[0-9a-fA-F]{6}", strings["tint"])
            or strings["accent"] not in ("amethyst", "emerald", "amber")
            or strings["state"] not in ("active", "retired", "disabled")
        ):
            raise SocialError("Invalid cosmetic definition")
        cosmetics.append(
            CosmeticSet(
                strings["key"],
                strings["name"],
                strings["artwork"],
                strings["tint"],
                strings["accent"],
                strings["description"],
                cast(Literal["active", "retired", "disabled"], strings["state"]),
            )
        )
    if len({c.key for c in cosmetics}) != len(cosmetics):
        raise SocialError("Duplicate cosmetic ID")
    return CosmeticCollection(revision, tuple(cosmetics))


def load_cosmetic_collection() -> CosmeticCollection:
    """Đọc một lần khi dựng UI; parser mạng không đọc tài nguyên."""
    resource = files("nostalgia.social").joinpath("cosmetics.json")
    return parse_cosmetic_collection(json.loads(resource.read_text(encoding="utf-8")))


def can_equip_cosmetic(collection: CosmeticCollection, decor: str, current: str) -> bool:
    if decor == "none":
        return True
    return any(
        c.key == decor and (c.state == "active" or (c.state == "retired" and decor == current))
        for c in collection.sets
    )
