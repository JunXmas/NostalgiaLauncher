"""Danh mục mở rộng được; mã mới không làm hỏng hồ sơ của máy khách cũ."""

from dataclasses import asdict, replace

import pytest

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue
from nostalgia.social.cosmetic import (
    can_equip_cosmetic,
    load_cosmetic_collection,
    parse_cosmetic_collection,
)
from nostalgia.social.parse import decor
from nostalgia.social.profile_parse import parse_profile


def test_lifecycle_keeps_retired_appearance_but_denies_new_selection() -> None:
    collection = load_cosmetic_collection()
    collection = replace(
        collection,
        sets=(
            replace(collection.sets[0], state="retired"),
            replace(collection.sets[1], state="disabled"),
            replace(collection.sets[2], key="moonlight"),
        ),
    )
    assert can_equip_cosmetic(collection, "amethyst", "amethyst")
    assert not can_equip_cosmetic(collection, "amethyst", "none")
    assert not can_equip_cosmetic(collection, "emerald", "emerald")
    assert can_equip_cosmetic(collection, "moonlight", "none")
    assert can_equip_cosmetic(collection, "none", "emerald")
    assert not can_equip_cosmetic(collection, "unknown", "unknown")


@pytest.mark.parametrize(
    "change",
    [
        {"key": "../secret"},
        {"artwork": "https://example.com/a"},
        {"key": "none"},
        {"state": "unexpected"},
        {"accent": "admin"},
        {"tint": "red"},
        {"name": ""},
    ],
)
def test_manifest_rejects_invalid_definitions(change: dict[str, str]) -> None:
    values = asdict(load_cosmetic_collection().sets[0]) | change
    with pytest.raises(SocialError):
        parse_cosmetic_collection({"schema": 1, "revision": 1, "items": [values]})


def test_duplicate_ids_and_unsupported_schema_are_rejected() -> None:
    values = asdict(load_cosmetic_collection().sets[0])
    documents: list[JsonValue] = [
        {"schema": 1, "revision": 1, "items": [values, values]},
        {"schema": 2, "revision": 1, "items": [values]},
        {"schema": 1, "revision": True, "items": [values]},
    ]
    for document in documents:
        with pytest.raises(SocialError):
            parse_cosmetic_collection(document)


def test_new_service_ids_survive_parsing_without_becoming_asset_paths() -> None:
    document: dict[str, JsonValue] = {
        "account_id": "misa",
        "name": "Misa",
        "decor": "moonlight-2027",
    }
    assert parse_profile(document).details.decor == "moonlight-2027"
    assert decor("moonlight-2027") == "moonlight-2027"
    for value in ("../../secret", "file:///secret", "x" * 65):
        with pytest.raises(SocialError):
            parse_profile(document | {"decor": value})


def test_profile_parses_owned_cosmetics_without_granting_unknown_payloads() -> None:
    document: dict[str, JsonValue] = {
        "account_id": "player",
        "name": "Player",
        "owned_cosmetics": ["amethyst"],
    }
    assert parse_profile(document).owned_cosmetics == ("amethyst",)
    invalid_values: tuple[JsonValue, ...] = (
        ["amethyst", "amethyst"],
        ["../model"],
        ["none"],
        [True],
    )
    for invalid in invalid_values:
        with pytest.raises(SocialError):
            parse_profile(document | {"owned_cosmetics": invalid})
