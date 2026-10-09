"""Phần bộ lọc của cầu nối nội dung: loader, phiên bản game, và loại đang xem.

Tách khỏi `content_bridge.py` cho mỗi file ngắn; cùng một QObject nhìn từ QML.

Luật đáng nhớ ở đây: bộ lọc MẶC ĐỊNH bám theo bản chơi đích, nhưng modpack thì không —
modpack tạo ra bản chơi mới chứ không cài vào bản nào, nên ghim nó vào phiên bản của bản
chơi đang chọn là giấu mất gần hết kho (phản hồi thật của người chơi). Và chỉ bộ lọc mặc
định mới được đặt lại: người dùng đã tự tick thì giữ nguyên ý họ.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.content.model import ContentKind
from nostalgia.ui.modpack_bridge import ModpackContentBridge


class FilterContentBridge(ModpackContentBridge):
    filtersChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(launcher, parent)
        # Rỗng nghĩa là không lọc theo tiêu chí đó.
        self._loaders: list[str] = []
        self._game_versions: list[str] = []
        self._kind: ContentKind = "mod"
        self._filters_touched = False
        self._browse_instance_id = ""

    @Property(str, notify=filtersChanged)
    def browseInstanceId(self) -> str:
        return self._browse_instance_id

    @Slot(str, result=bool)
    def pinBrowseTarget(self, instance_id: str) -> bool:
        """Duyệt từ quản lý chỉ cài vào target đã chọn, không đổi target từ popup dự án."""
        if not self._target or self._target.instance_id != instance_id:
            return False
        self._browse_instance_id = instance_id
        self._filters_touched = False
        self.apply_default_filters()
        self.filtersChanged.emit()
        return True

    @Slot()
    def unpinBrowseTarget(self) -> None:
        self._browse_instance_id = ""
        self.filtersChanged.emit()

    @Property(list, notify=filtersChanged)
    def selectedLoaders(self) -> list[str]:
        return list(self._loaders)

    @Property(list, notify=filtersChanged)
    def selectedGameVersions(self) -> list[str]:
        return list(self._game_versions)

    @Slot(str, bool)
    def setLoaderSelected(self, loader_name: str, selected: bool) -> None:
        if self._browse_instance_id:
            return
        self._loaders = _toggle(self._loaders, loader_name, selected)
        self._filters_touched = True
        self.filtersChanged.emit()

    @Slot(str, bool)
    def setGameVersionSelected(self, game_version: str, selected: bool) -> None:
        if self._browse_instance_id:
            return
        self._game_versions = _toggle(self._game_versions, game_version, selected)
        self._filters_touched = True
        self.filtersChanged.emit()

    @Slot()
    def clearGameVersions(self) -> None:
        if self._browse_instance_id:
            return
        self._game_versions = []
        self._filters_touched = True
        self.filtersChanged.emit()

    @Slot()
    def clearLoaders(self) -> None:
        if self._browse_instance_id:
            return
        self._loaders = []
        self._filters_touched = True
        self.filtersChanged.emit()

    # ----- loại nội dung đang xem -----

    @Property(str, notify=filtersChanged)
    def kind(self) -> str:
        return self._kind

    @Slot(str)
    def setKind(self, content_kind: str) -> None:
        if self._browse_instance_id and content_kind not in ("mod", "shader", "resourcepack"):
            return
        if content_kind == self._kind:
            return
        self._kind = content_kind  # type: ignore[assignment]
        if not self._filters_touched:
            self.apply_default_filters()
        self.filtersChanged.emit()

    def apply_default_filters(self) -> None:
        """Lọc mặc định: theo bản chơi đích, trừ modpack thì không lọc gì."""
        if self._kind == "modpack" or self._target is None:
            self._loaders = []
            self._game_versions = []
            return
        self._loaders = (
            [self._target.loader_kind]
            if self._kind == "mod" and self._target.loader_kind != "vanilla"
            else []
        )
        self._game_versions = [self._target.game_version]


def _toggle(values: list[str], value: str, selected: bool) -> list[str]:
    without = [existing for existing in values if existing != value]
    return [*without, value] if selected else without
