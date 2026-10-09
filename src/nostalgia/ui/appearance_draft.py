"""Bản xem trước riêng theo tài khoản; chưa bấm Lưu thì không chạm dịch vụ skin."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppearanceDraft:
    account_id: str = ""
    source: str = ""
    slim: bool = False
    cape_source: str = ""
    cape_id: str = ""
    entry_id: str = ""

    def skin_matches(self, other: AppearanceDraft) -> bool:
        return self.slim == other.slim and (
            self.entry_id == other.entry_id
            if self.entry_id and other.entry_id
            else self.source == other.source
        )


@dataclass(frozen=True, slots=True)
class AppearanceResult:
    draft: AppearanceDraft
    skin_saved: bool = False
    cape_saved: bool = False
    error: str = ""
