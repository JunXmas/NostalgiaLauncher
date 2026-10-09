"""Cửa cài mod từ máy: nạp bản chơi ở thời điểm xác nhận, không tin đường dẫn từ UI."""

from pathlib import Path

from nostalgia.facade.context import LauncherContext
from nostalgia.instance.store import game_dir_of, load_instance
from nostalgia.model.local_mod import LocalModImport


class LocalModOperations(LauncherContext):
    __slots__ = ()

    def install_local_mods(
        self, instance_id: str, sources: tuple[Path, ...], *, replace_existing: bool = False
    ) -> LocalModImport:
        """Không mạng. Chép vào bản chơi đã chọn, sao lưu nếu người chơi cho thay file."""
        from nostalgia.content.local_mod import install_local_mods

        instance = load_instance(self.paths, instance_id)
        return install_local_mods(
            game_dir_of(self.paths, instance), sources, replace_existing=replace_existing
        )
