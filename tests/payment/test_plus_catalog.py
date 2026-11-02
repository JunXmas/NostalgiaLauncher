"""Một Nostalgia+ hai giá; offer id và giá cũ chỉ còn trong catalog, không lời hứa chưa chạy."""

from __future__ import annotations

import re

from nostalgia.payment.catalog import LIFETIME, OFFERS, YEARLY
from source_tree import PACKAGE_ROOT, REPOSITORY_ROOT

OLD_OFFERS = re.compile(
    r"plus-(month-v1|half-year-v1|year-v2|lifetime-v1)|\b(29|69|109|209)[.,]?000\b"
)
QML = PACKAGE_ROOT / "ui" / "qml"


def test_one_product_two_prices() -> None:
    assert (YEARLY.amount, YEARLY.duration_months, YEARLY.lifetime) == (79_000, 12, False)
    assert (LIFETIME.amount, LIFETIME.lifetime) == (199_000, True)
    assert OFFERS == (YEARLY, LIFETIME)


def test_old_offer_ids_and_prices_live_only_in_the_catalog() -> None:
    hits = [
        str(path.relative_to(REPOSITORY_ROOT))
        for path in sorted(PACKAGE_ROOT.rglob("*"))
        if path.suffix in {".py", ".qml", ".js"}
        and path.name != "catalog.py"
        and OLD_OFFERS.search(path.read_text(encoding="utf-8"))
    ]
    assert hits == []


def test_sales_page_lists_only_benefits_that_run_and_no_paid_tier_names() -> None:
    page = "".join(
        (QML / "app" / name).read_text(encoding="utf-8")
        for name in ("PaymentPlans.qml", "SupportDialog.qml")
    )
    for promise in ("sắp có", "Sắp có", "relay", "1 trong 3", "Dự kiến", "Host server ·"):
        assert promise not in page
    shipped = "".join(path.read_text(encoding="utf-8") for path in QML.rglob("*.qml"))
    assert not re.search(r"Pro\+|Ultimate|Pro, Max|\"Max\"", shipped)
    # Ba quyền lợi trên trang bán đều có nút thật nối vào cầu nối, mở theo cùng cờ `plus`.
    perks = (QML / "app" / "ProfilePerks.qml").read_text(encoding="utf-8")
    assert "socialBridge.setProfile(" in perks and "socialBridge.downloadEarlyPreview()" in perks
    assert "socialBridge.account.plus === true" in (QML / "app" / "CosmeticLibrary.qml").read_text(
        encoding="utf-8"
    )
