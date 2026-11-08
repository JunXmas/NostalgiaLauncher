"""Marketplace Qt thật: skin riêng, xác nhận mua, tủ đồ và xóa phiên."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from market_fixture import MarketFixture
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def market_preview(social_preview: tuple[Any, ...]) -> tuple[Any, ...]:
    _launcher, _gateway, view, root_item, *_ = social_preview
    _gateway.snapshot = replace(_gateway.snapshot, invitations=())
    fixture = MarketFixture()
    market = view.rootContext().contextProperty("marketBridge")
    renderer = view.rootContext().contextProperty("marketPreviews")
    market._gateway = fixture
    renderer._gateway = fixture
    login_preview(social_preview)
    root_item.setProperty("currentIndex", 8)
    wait_until(
        lambda: market.details["enabled"] and market.details["balance"] == 100 and not market.busy
    )
    wait_until(lambda: (bool(renderer.source) or bool(renderer.note)) and not renderer.busy)
    assert renderer.source, renderer.note
    return social_preview, fixture, market, renderer


def test_preview_and_purchase_equipping(market_preview: tuple[Any, ...], tmp_path: Path) -> None:
    preview, fixture, market, _renderer = market_preview
    _, _, view, root_item, *_ = preview
    assert find_control(root_item, "marketPlayerPreview").property("source").toString()
    press(view, find_control(root_item, "marketBuy"))
    wait_until(lambda: bool(market.details["quote"]) and not market.busy)
    assert not fixture.keys
    press(view, find_control(root_item, "marketConfirmBuy"))
    wait_until(lambda: market.details["balance"] == 40 and not market.busy)
    assert len(fixture.keys) == 1
    assert market.details["owned"][0]["instance_id"] == "owned-one"
    market.equip("owned-one", "head")
    wait_until(lambda: market.details["owned"][0]["equipped_slot"] == "head" and not market.busy)
    root_item.setProperty("currentIndex", 8)
    view.grabWindow().save(str(tmp_path / "marketplace.png"))


def test_escape_cancels_quote_without_spending_and_logout_clears_wallet(
    market_preview: tuple[Any, ...],
) -> None:
    preview, fixture, market, _renderer = market_preview
    _, _, view, root_item, social, *_ = preview
    press(view, find_control(root_item, "marketBuy"))
    wait_until(lambda: bool(market.details["quote"]) and not market.busy)
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: not market.details["quote"])
    assert not fixture.keys and market.details["balance"] == 100
    social._reset_session("test logout")
    assert market.details["balance"] == 0 and not market.details["owned"]


def test_daily_claim_and_opt_in_point_checkout(market_preview: tuple[Any, ...]) -> None:
    preview, fixture, market, _renderer = market_preview
    _, _, view, root_item, *_ = preview
    press(view, find_control(root_item, "marketTab-1"))
    wait_until(lambda: not market.busy)
    press(view, find_control(root_item, "marketClaimReward"))
    wait_until(lambda: market.details["rewards"]["claimed_today"] and not market.busy)
    assert market.details["balance"] == 100
    assert market.details["rewards"]["balance"] == 80
    assert not find_control(root_item, "marketClaimReward").property("clickable")
    press(view, find_control(root_item, "marketTab-0"))
    press(view, find_control(root_item, "marketUsePoints"), Qt.Key.Key_Space)
    press(view, find_control(root_item, "marketBuy"))
    wait_until(lambda: bool(market.details["quote"]) and not market.busy)
    assert market.details["quote"]["base_price"] == 60
    assert market.details["quote"]["reward_points"] == 15
    assert market.details["quote"]["price"] == 45
    press(view, find_control(root_item, "marketConfirmBuy"))
    wait_until(lambda: market.details["balance"] == 55 and not market.busy)
    assert fixture.rewards.balance == 65 and len(fixture.keys) == 1


@pytest.mark.parametrize("language,scale", [("en", 100), ("vi", 150)])
def test_wallet_render_small_window_and_large_text(
    market_preview: tuple[Any, ...],
    language: str,
    scale: int,
    tmp_path: Path,
) -> None:
    preview, _fixture, market, _renderer = market_preview
    _, _, view, root_item, *_ = preview
    view.resize(1024, 680)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, True, False, language
    )
    press(view, find_control(root_item, "marketTab-1"))
    wait_until(lambda: not market.busy)
    QTest.qWait(300)
    card = find_control(root_item, "marketRewardCard")
    claim = find_control(root_item, "marketClaimReward")
    position = claim.mapToItem(card, 0, claim.height())
    assert position.y() <= card.height()-12
    assert claim.width() <= card.width()-32
    assert view.grabWindow().save(str(tmp_path / f"market-wallet-{language}-{scale}.png"))
