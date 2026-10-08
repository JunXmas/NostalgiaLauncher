"""Pack gốc và mod công khai được tải từ nguồn; phần riêng lấy đúng byte của host."""

import hashlib
from dataclasses import replace
from pathlib import Path

from nostalgia.content import modrinth
from nostalgia.content.installed import load_ledger
from nostalgia.content.local_metadata import read_labels
from nostalgia.content.pack_origin import load_pack_origin, save_pack_origin
from nostalgia.content.pack_reference import parse_pack_reference, reference_document
from nostalgia.content.sync_icon import archive_icon, safe_sync_icon, sync_title
from nostalgia.errors import ContentError, IntegrityError, MultiplayerError, NetworkError
from nostalgia.facade.sync_download import SyncDownloadOperations
from nostalgia.model.pack import PackReference
from nostalgia.multiplayer.sync_manifest import SYNC_DIRECTORIES
from nostalgia.multiplayer.sync_model import RoomSyncGateway, SyncFile, SyncManifest, SyncSnapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn


def matches_sync_file(path: Path, sync_file: SyncFile) -> bool:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != sync_file.size:
        return False
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest() == sync_file.sha256


class SyncSourceOperations(SyncDownloadOperations):
    __slots__ = ()

    def describe_sync_snapshot(self, game_dir: Path, snapshot: SyncSnapshot) -> SyncSnapshot:
        origin = load_pack_origin(game_dir)
        manifest = snapshot.manifest
        if origin and (origin.game_version, origin.loader_kind, origin.loader_version) != (
            manifest.game_version,
            manifest.loader_kind,
            manifest.loader_version,
        ):
            origin = None
        base_files = (
            {sync_file.relative_path: sync_file for sync_file in origin.files} if origin else {}
        )
        ledger_files = {
            folder: {
                ledger_entry.file_name: ledger_entry
                for ledger_entry in load_ledger(game_dir / folder).values()
            }
            for folder in SYNC_DIRECTORIES
        }
        files: list[SyncFile] = []
        icon_budget = 512 * 1024
        for sync_file in manifest.files:
            baseline = base_files.get(sync_file.relative_path)
            from_base = baseline is not None and (baseline.sha256, baseline.size) == (
                sync_file.sha256,
                sync_file.size,
            )
            folder, file_name = sync_file.relative_path.split("/", 1)
            ledger_entry = ledger_files[folder].get(file_name.removesuffix(".disabled"))
            source = (
                PackReference(
                    "curseforge" if ledger_entry.source == "curseforge" else "modrinth",
                    ledger_entry.project_id,
                    ledger_entry.version_id,
                )
                if ledger_entry
                and ledger_entry.source in ("modrinth", "curseforge")
                and ledger_entry.project_id
                and ledger_entry.version_id
                else None
            )
            if source is not None:
                try:
                    source = parse_pack_reference(reference_document(source))
                except ValueError:
                    source = None
            icon_url = safe_sync_icon(ledger_entry.icon_url) if ledger_entry else ""
            if folder in ("mods", "resourcepacks", "shaderpacks"):
                icon_url = icon_url or archive_icon(snapshot.folder / sync_file.relative_path)
            if len(icon_url) > icon_budget:
                icon_url = ""
            icon_budget -= len(icon_url)
            title = (
                ledger_entry.title
                if ledger_entry
                else read_labels(snapshot.folder / sync_file.relative_path)[0]
                if folder == "mods"
                else ""
            )
            files.append(
                replace(
                    sync_file,
                    source=source if not from_base else None,
                    from_base=from_base,
                    title=sync_title(title),
                    icon_url=icon_url,
                )
            )
        return replace(
            snapshot,
            manifest=replace(
                manifest, files=tuple(files), base_pack=origin.reference if origin else None
            ),
        )

    def sync_room_files(
        self,
        gateway: RoomSyncGateway,
        room_code: str,
        manifest: SyncManifest,
        stage: Path,
        *,
        cancel_token: CancelToken,
        on_progress: ProgressFn,
        install_base: bool = True,
        reused_paths: frozenset[str] = frozenset(),
    ) -> bool:
        base_installed = False
        if manifest.base_pack and install_base:
            try:
                self.sync_pack_source(
                    manifest.base_pack,
                    stage,
                    manifest.game_version,
                    manifest.loader_kind,
                    manifest.loader_version,
                    cancel_token=cancel_token,
                    on_progress=on_progress,
                )
                save_pack_origin(
                    stage,
                    manifest.base_pack,
                    manifest.game_version,
                    manifest.loader_kind,
                    manifest.loader_version,
                )
                base_installed = True
            except (ContentError, NetworkError, IntegrityError):
                # Host vẫn giữ ảnh chụp đầy đủ: nguồn gốc mất file không làm mất phần custom.
                pass
        desired = {sync_file.relative_path for sync_file in manifest.files}
        for directory in SYNC_DIRECTORIES:
            folder = stage / directory
            if folder.is_symlink():
                raise ContentError("Pack gốc chứa liên kết thư mục.")
            for path in folder.rglob("*") if folder.is_dir() else ():
                if (
                    path.is_file()
                    and path.relative_to(stage).as_posix() not in desired
                    and not path.name.startswith(".")
                ):
                    path.unlink()
        with self.make_http_client() as http_client:
            unknown = tuple(
                sync_file.sha1
                for sync_file in manifest.files
                if sync_file.relative_path not in reused_paths
                and sync_file.sha1
                and sync_file.source is None
                and not matches_sync_file(stage / sync_file.relative_path, sync_file)
                and sync_file.relative_path.split("/")[0]
                in ("mods", "resourcepacks", "shaderpacks")
            )
            try:
                versions = (
                    modrinth.lookup_versions_by_hash(
                        http_client, unknown, endpoints=self.endpoints, cancel_token=cancel_token
                    )
                    if unknown
                    else {}
                )
            except (ContentError, NetworkError):
                versions = {}
            for sync_file in manifest.files:
                cancel_token.raise_if_cancelled()
                target = stage / sync_file.relative_path
                if sync_file.relative_path in reused_paths or matches_sync_file(target, sync_file):
                    continue
                source = sync_file.source
                matched = versions.get(sync_file.sha1)
                if source is None and matched and matched.file_sha1 == sync_file.sha1:
                    source = PackReference("modrinth", matched.project_id, matched.version_id)
                payload = (
                    self._fetch_sync_source(http_client, source, sync_file, cancel_token)
                    if source
                    else None
                )
                if payload is None:
                    download_cancelable = getattr(gateway, "download_cancelable", None)
                    payload = (
                        download_cancelable(room_code, sync_file, cancel_token)
                        if download_cancelable
                        else gateway.download(room_code, sync_file)
                    )
                if (
                    len(payload) != sync_file.size
                    or hashlib.sha256(payload).hexdigest() != sync_file.sha256
                ):
                    raise MultiplayerError("File modpack không khớp SHA-256; đồng bộ đã dừng.")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                target.chmod(0o600)
        return base_installed
