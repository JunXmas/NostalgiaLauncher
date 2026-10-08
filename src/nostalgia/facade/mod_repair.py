"""Façade kiểm/sửa mod, dùng bản chơi thật và thư mục game riêng."""

from __future__ import annotations

from collections.abc import Callable

from nostalgia.facade.loaders import LoaderOperations
from nostalgia.facade.sync_loader import resolve_sync_loader
from nostalgia.instance.store import game_dir_of, load_instance
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.model import ModScan
from nostalgia.modcheck.scan import build_scan
from nostalgia.modloader.model import detect_loader_kind
from nostalgia.modrepair.model import RepairGateway, RepairPlan, RepairScan
from nostalgia.modrepair.transaction import apply_plan, latest_repair, undo_repair
from nostalgia.repo.version_repo import VersionRepository


class ModRepairOperations(LoaderOperations):
    __slots__ = ()

    def scan_instance_mods(self, instance_id: str) -> ModScan:
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        loader_kind = detect_loader_kind(instance.version_id)
        loader_version = resolve_sync_loader(
            loader_kind, version_meta.libraries, version_meta.jar_owner_id
        )
        java_major = (
            version_meta.java_runtime.major_version if version_meta.java_runtime else None
        ) or 8
        scan = build_scan(
            scan_archives(game_dir_of(self.paths, instance), loader_kind),
            version_meta.jar_owner_id,
            loader_kind,
            loader_version,
            java_major,
        )
        return with_game_logs(scan, game_dir_of(self.paths, instance))

    def scan_mod_repair(self, instance_id: str) -> RepairScan:
        instance = load_instance(self.paths, instance_id)
        return RepairScan(
            self.scan_instance_mods(instance_id), latest_repair(game_dir_of(self.paths, instance))
        )

    def apply_mod_repair(
        self,
        instance_id: str,
        scan: ModScan,
        plan: RepairPlan,
        gateway: RepairGateway,
        is_running: Callable[[], bool],
    ) -> str:
        instance = load_instance(self.paths, instance_id)
        with self.make_http_client() as http_client:
            return apply_plan(
                game_dir_of(self.paths, instance), scan, plan, gateway, http_client, is_running
            )

    def undo_mod_repair(
        self, instance_id: str, receipt_id: str, is_running: Callable[[], bool]
    ) -> None:
        instance = load_instance(self.paths, instance_id)
        undo_repair(game_dir_of(self.paths, instance), receipt_id, is_running)
