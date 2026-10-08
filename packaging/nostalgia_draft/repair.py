"""Conservative local planner for draft QA; production keeps server authorization."""

from __future__ import annotations

import secrets
import time

from nostalgia.errors import ContentError
from nostalgia.modcheck.model import ModScan
from nostalgia.modrepair.gateway import scan_hash
from nostalgia.modrepair.model import RepairChange, RepairPlan
from nostalgia_draft.social import ReviewSocial


class ReviewRepair:
    def __init__(self, social: ReviewSocial) -> None:
        self._social = social
        self._plans: dict[str, RepairPlan] = {}

    def fetch_plan(self, scan: ModScan, selection: str = "") -> RepairPlan:
        del selection
        changes: dict[str, RepairChange] = {}
        unresolved = []
        for finding in scan.findings:
            if finding.code not in ("duplicate", "loader", "conflict"):
                unresolved.append(finding.reason)
                continue
            archive = next(a for a in scan.archives if a.file_name == finding.file_name)
            changes[archive.file_name] = RepairChange(
                "disable", archive.file_name, archive.sha256, "", 0, "", finding.reason
            )
        plan = RepairPlan(
            secrets.token_hex(32),
            scan_hash(scan),
            int(time.time()) + 900,
            tuple(changes.values()),
            tuple(unresolved),
        )
        self._plans = {plan.plan_id: plan}
        return plan

    def authorize(self, plan: RepairPlan) -> None:
        if (
            not self._social.access_token
            or self._plans.get(plan.plan_id) != plan
            or time.time() >= plan.expires_at
        ):
            raise ContentError("Phương án TEST hết hạn hoặc không khớp; hãy quét lại.")
        del self._plans[plan.plan_id]
