"""Người mua bốn gói cũ giữ nguyên quyền và hạn; Ultimate cũ vẫn là mua đứt."""

from __future__ import annotations

import json

import pytest
from test_social_gateway import snapshot_document

from nostalgia.errors import SocialError
from nostalgia.social.parse import badge, parse_snapshot


@pytest.mark.parametrize(
    ("plan", "until", "lifetime"),
    [
        ("plus-month-v1", 4_000_000_000, False),
        ("plus-half-year-v1", 4_000_000_000, False),
        ("plus-year-v2", 4_000_000_000, False),
        ("plus-lifetime-v1", 0, True),
        ("plus-year-v3", 4_000_000_000, False),
        ("plus-lifetime-v2", 0, True),
    ],
)
def test_me_with_old_and_new_plans_keeps_rights_and_expiry(
    plan: str, until: int, lifetime: bool
) -> None:
    document = json.loads(json.dumps(snapshot_document()))
    document["account"].update(plus_plan=plan, plus_until=until, plus_lifetime=lifetime)
    account = parse_snapshot(document).account
    assert (account.plus_plan, account.plus_until, account.plus_lifetime) == (
        plan,
        until,
        lifetime,
    )


@pytest.mark.parametrize("plan", ["plus-year-v2", "plus-year-v3", "plus-ultimate"])
def test_only_lifetime_plans_may_claim_lifetime(plan: str) -> None:
    document = json.loads(json.dumps(snapshot_document()))
    document["account"].update(plus_plan=plan, plus_lifetime=True)
    with pytest.raises(SocialError):
        parse_snapshot(document)


def test_old_worker_badges_become_early_supporter() -> None:
    for old in ("Đồng hành", "Tiên phong", "Sáng lập"):
        assert badge(old) == "Người ủng hộ sớm"
    assert badge("Nostalgia+") == "Nostalgia+"
    with pytest.raises(SocialError):
        badge("Admin")
