"""Nostalgia+: một sản phẩm, hai cách mua. Mọi offer id và giá của launcher chỉ nằm ở đây.

Giá ở đây chỉ để hiện trước khi máy chủ trả lời; giá tính tiền luôn là giá máy chủ báo.
"""

from __future__ import annotations

from nostalgia.payment.model import PaymentOffer

YEARLY = PaymentOffer("plus-year-v3", 79_000, 79_000, 12)
LIFETIME = PaymentOffer("plus-lifetime-v2", 199_000, 199_000, 0, lifetime=True)
OFFERS = (YEARLY, LIFETIME)

# Bốn gói bán trước Nostalgia+ (29k/69k/109k/209k). Người đã mua giữ nguyên quyền và hạn,
# mang nhãn "Người ủng hộ sớm"; gói mua đứt cũ vẫn là mua đứt.
EARLY_SUPPORTER_PLANS = frozenset(
    {"plus-month-v1", "plus-half-year-v1", "plus-year-v2", "plus-lifetime-v1"}
)
PLANS = EARLY_SUPPORTER_PLANS | {offer.offer_id for offer in OFFERS}
LIFETIME_PLANS = frozenset({LIFETIME.offer_id, "plus-lifetime-v1"})

PLUS_BADGE = "Nostalgia+"
EARLY_SUPPORTER_BADGE = "Người ủng hộ sớm"
# Huy hiệu của bốn gói cũ mà Worker chưa cập nhật vẫn gửi kèm hồ sơ bạn bè.
OLD_BADGES = frozenset({"Đồng hành", "Tiên phong", "Sáng lập"})
