"""So khớp pack của host và tạo lựa chọn nội dung cho khách trước khi tải."""

from nostalgia.errors import MultiplayerError
from nostalgia.facade.sync_source import SyncSourceOperations
from nostalgia.instance.model import Instance
from nostalgia.instance.store import list_instances
from nostalgia.instance.sync_receipt import load_sync_receipt, receipt_identity
from nostalgia.model.pack import SyncChoice, SyncPackIdentity, SyncReview
from nostalgia.multiplayer.sync_model import SyncManifest

OPTIONAL_DIRECTORIES = frozenset({"mods", "resourcepacks", "shaderpacks"})


class SyncReviewOperations(SyncSourceOperations):
    __slots__ = ()

    def matched_room_instance(self, manifest: SyncManifest) -> Instance | None:
        if not manifest.owner_id or not manifest.pack_id:
            return None
        matches = tuple(
            instance
            for instance in list_instances(self.paths)
            if receipt_identity(self.paths, instance.instance_id)
            == SyncPackIdentity(manifest.owner_id, manifest.pack_id)
        )
        if len(matches) > 1:
            raise MultiplayerError(
                "Có nhiều bản chơi cùng dấu vết đồng bộ. "
                "Hãy gỡ bản sao để chọn đúng bản cần cập nhật."
            )
        return matches[0] if matches else None

    def review_room_modpack(self, manifest: SyncManifest) -> SyncReview:
        instance = self.matched_room_instance(manifest)
        receipt = load_sync_receipt(self.paths, instance.instance_id) if instance else None
        previous = (
            {sync_file.relative_path.removesuffix(".disabled") for sync_file in receipt.files}
            if receipt
            else set()
        )
        excluded = receipt.excluded_paths if receipt else frozenset()
        choices = tuple(
            SyncChoice(
                sync_file.relative_path,
                sync_file.title or sync_file.relative_path.split("/")[-1].removesuffix(".disabled"),
                sync_file.icon_url,
                sync_file.relative_path.split("/")[0],
                not sync_file.relative_path.endswith(".disabled"),
                sync_file.relative_path.removesuffix(".disabled") not in excluded
                and (
                    receipt is None or sync_file.relative_path.removesuffix(".disabled") in previous
                ),
                receipt is not None
                and sync_file.relative_path.removesuffix(".disabled") not in previous
                and sync_file.relative_path.removesuffix(".disabled") not in excluded,
            )
            for sync_file in manifest.files
            if sync_file.relative_path.split("/")[0] in OPTIONAL_DIRECTORIES
        )
        return SyncReview(
            choices, instance.instance_id if instance else "", instance.label if instance else ""
        )
