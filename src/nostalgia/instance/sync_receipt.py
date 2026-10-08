"""Dấu vết đồng bộ thuộc host đã xác thực và UUID pack, tuyệt đối không ghép theo tên."""

from nostalgia.errors import MultiplayerError, NostalgiaError
from nostalgia.model.json_value import as_list, as_mapping, as_string
from nostalgia.model.pack import PackFile, SyncPackIdentity, SyncReceipt
from nostalgia.multiplayer.sync_manifest import manifest_document, parse_sync_manifest, sync_path
from nostalgia.multiplayer.sync_model import SyncManifest
from nostalgia.storage.files import atomic_write_json, read_json
from nostalgia.storage.paths import DataPaths

RECEIPT_FILE = ".nostalgia-sync-receipt.json"


def load_sync_receipt(paths: DataPaths, instance_id: str) -> SyncReceipt | None:
    path = paths.instance_dir(instance_id) / RECEIPT_FILE
    if not path.exists():
        return None
    try:
        if path.is_symlink() or path.stat().st_size > 2 * 1024**2:
            raise ValueError
        fields = as_mapping(read_json(path))
        if fields.get("instance_id") != instance_id:
            return None  # Bản chơi sao chép không được tự trở thành mục tiêu cập nhật.
        manifest = parse_sync_manifest(fields["manifest"])
        if not manifest.owner_id or not manifest.pack_id:
            raise ValueError
        excluded = frozenset(
            sync_path(value).removesuffix(".disabled")
            for value in as_list(fields.get("excluded_paths"))
            if isinstance(value, str)
        )
        return SyncReceipt(
            manifest.owner_id,
            manifest.pack_id,
            instance_id,
            manifest.game_version,
            manifest.loader_kind,
            manifest.loader_version,
            tuple(
                PackFile(sync_file.relative_path, sync_file.sha256, sync_file.size)
                for sync_file in manifest.files
            ),
            excluded,
        )
    except (NostalgiaError, OSError, KeyError, ValueError):
        raise MultiplayerError(
            "Dấu vết đồng bộ hỏng; dừng để tránh cập nhật nhầm bản chơi."
        ) from None


def save_sync_receipt(
    paths: DataPaths, instance_id: str, manifest: SyncManifest, excluded_paths: frozenset[str]
) -> None:
    if manifest.owner_id and manifest.pack_id:
        atomic_write_json(
            paths.instance_dir(instance_id) / RECEIPT_FILE,
            {
                "instance_id": instance_id,
                "manifest": manifest_document(manifest),
                "excluded_paths": [str(path) for path in sorted(excluded_paths)],
            },
            private=True,
        )


def receipt_identity(paths: DataPaths, instance_id: str) -> SyncPackIdentity:
    path = paths.instance_dir(instance_id) / RECEIPT_FILE
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 2 * 1024**2:
            return SyncPackIdentity()
        fields = as_mapping(read_json(path))
        if fields.get("instance_id") != instance_id:
            return SyncPackIdentity()
        manifest = as_mapping(fields.get("manifest"))
        return SyncPackIdentity(
            as_string(manifest.get("owner_id")) or "", as_string(manifest.get("pack_id")) or ""
        )
    except (OSError, NostalgiaError):
        return SyncPackIdentity()
