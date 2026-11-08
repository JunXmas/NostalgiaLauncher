"""Combo chỉ là cách bán: tủ đồ chứa item, không sinh quyền sở hữu cho cả bộ."""

import pytest

from nostalgia.errors import SocialError
from nostalgia.marketplace.parse import parse_product, parse_quote, parse_wardrobe
from nostalgia.model.json_value import JsonValue


def product(product_id: str = "crown", slot: str = "head") -> dict[str, JsonValue]:
    return {
        "product_id": product_id,
        "name_en": "Test item",
        "name_vi": "Món kiểm thử",
        "description_en": "Test only",
        "description_vi": "Chỉ kiểm thử",
        "slot": slot,
        "price": 60,
        "revision": 1,
        "asset_hash": "a" * 64,
        "kind": "item",
    }


def bundle() -> dict[str, JsonValue]:
    return {
        **product("set"),
        "kind": "bundle",
        "slot": "",
        "asset_hash": "",
        "members": [product(), product("shirt", "top")],
    }


def test_bundle_has_constituent_items_and_never_becomes_a_wardrobe_instance() -> None:
    offer = parse_product(bundle())
    assert offer.product_kind == "bundle" and not offer.asset_hash and not offer.slot
    assert [member.product_id for member in offer.members] == ["crown", "shirt"]
    with pytest.raises(SocialError):
        parse_wardrobe({"balance": 100, "owned": [bundle()]})


@pytest.mark.parametrize("slot", ["head", "top", "bottom", "feet", "back", "accessory"])
def test_all_six_equipment_slots_are_supported(slot: str) -> None:
    assert parse_product(product(slot=slot)).slot == slot


@pytest.mark.parametrize(
    "members",
    [
        [product()],
        [product(), product()],
        [product(), product("other-crown")],
        [product(), bundle()],
        [product(), product("set", "top")],
        [product(), {**product("shirt", "top"), "instance_id": "owned"}],
    ],
)
def test_invalid_or_recursive_bundle_members_never_reach_preview(members: list[JsonValue]) -> None:
    with pytest.raises(SocialError):
        parse_product({**bundle(), "members": members})


def test_quote_explains_how_many_items_are_already_owned() -> None:
    quote = parse_quote(
        {
            "quote_id": "quote",
            "product_id": "set",
            "price": 32,
            "base_price": 32,
            "reward_points": 0,
            "expires_at": 4_000_000_000,
            "item_count": 2,
            "owned_count": 1,
        }
    )
    assert quote.price == 32 and quote.item_count - quote.owned_count == 1


@pytest.mark.parametrize("total,owned", [(0, 0), (7, 0), (2, 2), (2, -1), (1, True)])
def test_quote_rejects_impossible_ownership_counts(total: int, owned: int) -> None:
    with pytest.raises(SocialError):
        parse_quote(
            {
                "quote_id": "quote",
                "product_id": "set",
                "price": 32,
                "base_price": 32,
                "reward_points": 0,
                "expires_at": 4_000_000_000,
                "item_count": total,
                "owned_count": owned,
            }
        )
