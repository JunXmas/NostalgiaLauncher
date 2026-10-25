"""Façade kiểm/sửa mod, dùng bản chơi thật và thư mục game riêng."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from nostalgia.content import modrinth
from nostalgia.content.installed import set_enabled
from nostalgia.errors import ContentError
from nostalgia.facade.content import ContentOperations
from nostalgia.facade.loaders import LoaderOperations
from nostalgia.facade.sync_loader import resolve_sync_loader
from nostalgia.instance.store import game_dir_of, load_instance, save_instance
from nostalgia.modcheck.archive import scan_archives
from nostalgia.modcheck.game_logs import with_game_logs
from nostalgia.modcheck.local_fix import LocalFix, pick_loader_version
from nostalgia.modcheck.model import ModScan
from nostalgia.modcheck.scan import build_scan
from nostalgia.modloader.model import detect_loader_kind
from nostalgia.modrepair.model import RepairGateway, RepairPlan, RepairScan
from nostalgia.modrepair.transaction import apply_plan, latest_repair, undo_repair
from nostalgia.repo.version_repo import VersionRepository


class ModRepairOperations(LoaderOperations, ContentOperations):
    __slots__ = ()

    def scan_instance_mods(self, instance_id: str) -> ModScan:
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        loader_kind = detect_loader_kind(instance.version_id)
        loader_version = resolve_sync_loader(
            loader_kind,
            version_meta.libraries,
            version_meta.jar_owner_id,
            game_arguments=version_meta.game_arguments,
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

    def apply_local_fix(self, instance_id: str, fix: LocalFix) -> str:
        """Sửa tại chỗ, không cần dịch vụ: nâng loader / tắt jar / cài phụ thuộc. CHẠM MẠNG
        (trừ tắt jar). Trả câu báo kết quả cho người chơi."""
        instance = load_instance(self.paths, instance_id)
        game_dir = game_dir_of(self.paths, instance)
        if fix.fix_kind == "disable":
            set_enabled(game_dir, "mod", fix.target, False)
            return f"Đã tắt {fix.target}. Bật lại được trong Nội dung đã cài."
        loader_kind = detect_loader_kind(instance.version_id)
        game_version = (
            VersionRepository(self.paths).load_version_meta(instance.version_id).jar_owner_id
        )
        if fix.fix_kind == "loader":
            available = tuple(
                v.loader_version for v in self.list_loader_versions(loader_kind, game_version)
            )
            chosen = pick_loader_version(available, fix.target)
            if not chosen:
                raise ContentError(f"Chưa có bản loader nào thoả {fix.target} cho {game_version}.")
            report = self.install_loader(loader_kind, game_version, chosen)
            save_instance(self.paths, replace(instance, version_id=report.version_meta.version_id))
            return f"Đã nâng loader lên {chosen}."
        # dependency: mã mod Fabric thường trùng slug Modrinth; không thấy thì nói thẳng.
        with self.make_http_client() as http_client:
            found = modrinth.fetch_projects(
                http_client, (fix.target,), "mod", endpoints=self.endpoints
            )
        project = next(iter(found.values()), None)
        if project is None:
            raise ContentError(f"Không tìm thấy {fix.target} trên Modrinth; hãy cài tay.")
        self.install_content(self.describe_content_target(instance_id), project)
        return f"Đã cài {project.title}."
