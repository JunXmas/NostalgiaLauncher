"""Phương án server ràng buộc với đúng bản kê; không có lệnh thực thi tùy ý."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from nostalgia.modcheck.model import ModScan


@dataclass(frozen=True, slots=True)
class RepairChange:
    operation: str
    file_name: str
    sha256: str
    url: str
    size: int
    sha512: str
    reason: str


@dataclass(frozen=True, slots=True)
class RepairPlan:
    plan_id: str
    scan_hash: str
    expires_at: int
    changes: tuple[RepairChange, ...]
    unresolved: tuple[str, ...]


class RepairGateway(Protocol):
    def fetch_plan(self, scan: ModScan) -> RepairPlan: ...
    def authorize(self, plan: RepairPlan) -> None: ...


@dataclass(frozen=True, slots=True)
class RepairScan:
    scan: ModScan
    receipt_id: str
