"""Present server-bound repair groups and verify the exact proposal the player chose."""

from __future__ import annotations

from typing import Any

from nostalgia.api import ModScan, RepairPlan
from nostalgia.errors import ContentError
from nostalgia.modrepair.model import RepairChange


def repair_cards(plan: RepairPlan | None, scan: ModScan | None) -> list[dict[str, Any]]:
    if not plan or not scan:
        return []
    groups: dict[str, list[RepairChange]] = {}
    for change in plan.changes:
        if change.group_id:
            groups.setdefault(change.group_id, []).append(change)
    versions = {
        mod.mod_id: mod.version_number for archive in scan.archives for mod in archive.descriptors
    }
    cards = []
    for group_id, changes in groups.items():
        additions = [change for change in changes if change.operation == "add"]
        visual = additions[0] if additions else changes[0]
        cards.append(
            {
                "groupId": group_id,
                "name": visual.project_name or group_id,
                "icon": visual.icon_url,
                "currentVersion": versions.get(group_id, "Chưa cài"),
                "version": visual.version_number or "Giữ bản không trùng",
                "minecraft": scan.game_version,
                "loader": scan.loader_kind,
                "reason": visual.reason,
                "downloads": len(additions),
                "isReplacement": bool(additions),
                "canReplace": group_id not in plan.blocked_groups,
                "files": [change.file_name for change in changes],
            }
        )
    return cards


def check_chosen_group(shown: RepairPlan, fresh: RepairPlan, selection: str) -> None:
    expected = tuple(change for change in shown.changes if change.group_id == selection)

    def change_fingerprint(change: RepairChange) -> tuple[object, ...]:
        return (
            change.operation,
            change.file_name,
            change.sha256,
            change.url,
            change.size,
            change.sha512,
            change.group_id,
            change.version_number,
        )

    if (
        not expected
        or not fresh.partial
        or fresh.unresolved
        or selection in fresh.blocked_groups
        or selection in shown.blocked_groups
        or tuple(map(change_fingerprint, expected)) != tuple(map(change_fingerprint, fresh.changes))
    ):
        raise ContentError(
            "Phương án đã thay đổi hoặc còn lỗi chưa xác minh. Hãy lập lại phương án."
        )
