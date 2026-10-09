"""Log-based repair may keep old unrelated warnings; new/touched findings still block."""

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
        if (not plan.partial and not scan.diagnostics)
        or finding.severity == "error"
        or finding not in scan.findings
        or finding.file_name in touched
        or finding.mod_id in targets
    )
