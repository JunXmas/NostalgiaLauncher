"""Kiểm kiểu và giới hạn phản hồi trước khi đưa sang UI."""

import re
from dataclasses import replace

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue, as_mapping
from nostalgia.model.marketplace import (
    CoinOffer,
    CoinOrder,
    MarketCatalog,
    MarketProduct,
    MarketQuote,
    MarketRewards,
    Wardrobe,
)
from nostalgia.payment.qr_payload import render_payment_qr


def text(document: dict[str, JsonValue], field: str, maximum: int = 500) -> str:
    value = document.get(field)
    if not isinstance(value, str) or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise SocialError("Invalid marketplace text")
    return value


def identifier(document: dict[str, JsonValue], field: str) -> str:
    value = text(document, field, 96)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", value):
        raise SocialError("Invalid marketplace identifier")
    return value


def integer(document: dict[str, JsonValue], field: str) -> int:
    value = document.get(field)
    if type(value) is not int or not 0 <= value <= 9_007_199_254_740_991:
        raise SocialError("Invalid marketplace amount")
    return value


def rows(document: dict[str, JsonValue], field: str) -> list[JsonValue]:
    value = document.get(field)
    if not isinstance(value, list) or len(value) > 200:
        raise SocialError("Invalid marketplace list")
    return value


def parse_product_fields(fields: dict[str, JsonValue]) -> MarketProduct:
    instance_id = identifier(fields, "instance_id") if fields.get("instance_id") else ""
    equipped = text(fields, "equipped_slot") if fields.get("equipped_slot") else ""
    return MarketProduct(
        identifier(fields, "product_id"),
        text(fields, "name_en", 80),
        text(fields, "name_vi", 80),
        text(fields, "description_en"),
        text(fields, "description_vi"),
        text(fields, "slot"),
        integer(fields, "price"),
        integer(fields, "revision"),
        text(fields, "asset_hash"),
        instance_id,
        equipped,
    )


def parse_item(value: JsonValue) -> MarketProduct:
    fields = as_mapping(value)
    product = parse_product_fields(fields)
    if (
        fields.get("kind", "item") != "item"
        or product.slot not in ("head", "top", "bottom", "feet", "back", "accessory")
        or not re.fullmatch("[a-f0-9]{64}", product.asset_hash)
        or product.equipped_slot not in ("", product.slot)
    ):
        raise SocialError("Invalid cosmetic product")
    return product


def parse_product(value: JsonValue) -> MarketProduct:
    fields = as_mapping(value)
    if fields.get("kind", "item") != "bundle":
        return parse_item(value)
    product = parse_product_fields(fields)
    if product.slot or product.asset_hash or product.instance_id or product.equipped_slot:
        raise SocialError("Invalid cosmetic bundle")
    members = tuple(parse_item(row) for row in rows(fields, "members"))
    if (
        not 2 <= len(members) <= 6
        or len({member.product_id for member in members}) != len(members)
        or len({member.slot for member in members}) != len(members)
        or any(member.instance_id or member.equipped_slot for member in members)
    ):
        raise SocialError("Invalid cosmetic bundle members")
    if any(member.product_id == product.product_id for member in members):
        raise SocialError("Bundle contains itself")
    return replace(product, product_kind="bundle", members=members)


def parse_catalog(value: JsonValue) -> MarketCatalog:
    fields = as_mapping(value)
    if fields.get("schema_version") != 1 or type(fields.get("enabled")) is not bool:
        raise SocialError("Unsupported marketplace schema")
    return MarketCatalog(
        fields["enabled"] is True,
        tuple(parse_product(row) for row in rows(fields, "products")),
        tuple(
            CoinOffer(
                identifier(as_mapping(row), "offer_id"),
                integer(as_mapping(row), "amount"),
                integer(as_mapping(row), "coins"),
            )
            for row in rows(fields, "coin_offers")
        ),
    )


def parse_wardrobe(value: JsonValue) -> Wardrobe:
    fields = as_mapping(value)
    return Wardrobe(
        integer(fields, "balance"), tuple(parse_item(row) for row in rows(fields, "owned"))
    )


def parse_quote(value: JsonValue) -> MarketQuote:
    fields = as_mapping(value)
    expires = fields.get("expires_at")
    if type(expires) is not int or expires <= 0:
        raise SocialError("Invalid quote expiry")
    item_count, owned_count = integer(fields, "item_count"), integer(fields, "owned_count")
    if not 1 <= item_count <= 6 or not 0 <= owned_count < item_count:
        raise SocialError("Invalid quote item counts")
    if integer(fields, "base_price") != integer(fields, "price") + integer(fields, "reward_points"):
        raise SocialError("Invalid quote discount")
    if integer(fields, "reward_points") and integer(fields, "price") == 0:
        raise SocialError("Invalid full-price reward")
    return MarketQuote(
        identifier(fields, "quote_id"),
        identifier(fields, "product_id"),
        integer(fields, "price"),
        expires,
        item_count,
        owned_count,
        integer(fields, "base_price"),
        integer(fields, "reward_points"),
    )


def parse_order(value: JsonValue) -> CoinOrder:
    fields = as_mapping(value)
    status = text(fields, "status")
    if status not in ("pending", "submitted", "paid", "rejected"):
        raise SocialError("Invalid coin order state")
    return CoinOrder(
        identifier(fields, "order_id"),
        integer(fields, "amount"),
        integer(fields, "coins"),
        status,
        text(fields, "bank_account"),
        text(fields, "bank_holder"),
        text(fields, "memo"),
        text(fields, "qr_payload", 512),
        render_payment_qr(text(fields, "qr_payload", 512))
        if status in ("pending", "submitted")
        else "",
    )


def parse_rewards(value: JsonValue) -> MarketRewards:
    fields = as_mapping(value)
    if any(type(fields.get(key)) is not bool for key in ("enabled", "member", "claimed_today")):
        raise SocialError("Invalid reward state")
    if fields.get("unit_coin_value") != 1 or integer(fields, "max_percent") > 99:
        raise SocialError("Unsupported reward policy")
    if integer(fields, "expiry_days") > 365:
        raise SocialError("Invalid reward expiry")
    return MarketRewards(
        fields["enabled"] is True,
        fields["member"] is True,
        fields["claimed_today"] is True,
        *(
            integer(fields, key)
            for key in (
                "balance",
                "daily_points",
                "max_percent",
                "expiry_days",
                "next_claim_at",
                "next_expiry_at",
                "expiring_points",
            )
        ),
    )
