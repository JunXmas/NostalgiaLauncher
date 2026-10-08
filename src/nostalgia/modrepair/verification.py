"""Partial repair may keep unrelated findings, but must fix every affected dependency."""

from nostalgia.modcheck.model import ModFinding, ModScan
from nostalgia.modrepair.model import RepairPlan


def remaining_findings(
    scan: ModScan, repaired: ModScan, plan: RepairPlan
) -> tuple[ModFinding, ...]:
    touched = {change.file_name for change in plan.changes}
    targets = {change.group_id for change in plan.changes if change.group_id}
    return tuple(
        finding
        for finding in repaired.findings
        if not plan.partial
        or finding not in scan.findings
        or finding.file_name in touched
        or finding.mod_id in targets
    )
