"""Slide quảng cáo trang chủ đọc từ feed trong kho GitHub (xem `content/promotions.py`)."""

from __future__ import annotations

from nostalgia.content.promotions import Promotion, load_promotions
from nostalgia.facade.context import LauncherContext


class PromotionOperations(LauncherContext):
    __slots__ = ()

    def load_promotions(self) -> tuple[Promotion, ...]:
        """Feed mới nhất, hoặc bản đệm khi offline/hỏng; rỗng thì ẩn slide. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            return load_promotions(
                self.paths.updates_dir / "promotions",
                http_client,
                self.endpoints.promotions,
                self.endpoints.promotion_hosts,
            )
