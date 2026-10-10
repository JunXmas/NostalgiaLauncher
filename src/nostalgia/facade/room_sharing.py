"""Lựa chọn đồng bộ thuộc từng bản chơi, độc lập với trạng thái bật mod trong game."""

from nostalgia.content.installed import list_installed
from nostalgia.content.sync_icon import archive_icon, safe_sync_icon, sync_title
from nostalgia.errors import NostalgiaError
from nostalgia.facade.context import LauncherContext
from nostalgia.instance.store import game_dir_of, load_instance
from nostalgia.model.json_value import as_list, as_mapping
from nostalgia.model.pack import SharedMod
from nostalgia.multiplayer.snapshot_integrity import verify_snapshot_source
from nostalgia.multiplayer.sync_manifest import sync_path
from nostalgia.multiplayer.sync_model import SyncSnapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import atomic_write_json, read_json


class RoomSharingOperations(LauncherContext):
    __slots__ = ()

    def verify_room_snapshot(
        self,
        instance_id: str,
        snapshot: SyncSnapshot,
        excluded_mods: frozenset[str],
        cancel_token: CancelToken,
    ) -> None:
        verify_snapshot_source(
            game_dir_of(self.paths, load_instance(self.paths, instance_id)),
            snapshot,
            excluded_mods,
            cancel_token,
        )

    def load_room_share_options(self, instance_id: str) -> frozenset[str]:
        game_dir = game_dir_of(self.paths, load_instance(self.paths, instance_id))
        path = game_dir / ".nostalgia-room-sharing.json"
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 256_000:
            return frozenset()
        try:
            fields = as_mapping(read_json(path))
            return frozenset(
                sync_path(value).removesuffix(".disabled")
                for value in as_list(fields.get("excluded_mods"))
                if isinstance(value, str) and value.startswith("mods/")
            )
        except (NostalgiaError, OSError, ValueError):
            return frozenset()

    def save_room_share_options(self, instance_id: str, excluded_mods: frozenset[str]) -> None:
        game_dir = game_dir_of(self.paths, load_instance(self.paths, instance_id))
        paths = sorted(
            sync_path(value).removesuffix(".disabled")
            for value in excluded_mods
            if value.startswith("mods/")
        )
        atomic_write_json(
            game_dir / ".nostalgia-room-sharing.json", {"excluded_mods": list(paths)}, private=True
        )

    def list_room_share_mods(self, instance_id: str) -> tuple[SharedMod, ...]:
        game_dir = game_dir_of(self.paths, load_instance(self.paths, instance_id))
        excluded = self.load_room_share_options(instance_id)
        return tuple(
            SharedMod(
                "mods/" + content.file_name + ("" if content.enabled else ".disabled"),
                sync_title(content.label),
                content.file_name,
                safe_sync_icon(content.icon_url)
                or archive_icon(
                    game_dir
                    / "mods"
                    / (content.file_name + ("" if content.enabled else ".disabled"))
                ),
                content.enabled,
                ("mods/" + content.file_name) not in excluded,
            )
            for content in list_installed(game_dir, "mod")
        )
