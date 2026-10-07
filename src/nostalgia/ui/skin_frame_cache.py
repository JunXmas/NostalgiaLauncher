"""Cache raster skin 3D theo cửa sổ, tối đa 32 frame (~4 MiB)."""

from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QImageReader

from nostalgia.ui.skin_mesh import SkinSurface, normalize_skin, skin_surfaces
from nostalgia.ui.skin_renderer import FRAME_COUNT, render_skin

MAX_FRAME_CACHE = 32
MAX_MESH_CACHE = 8
MAX_TEXTURE_BYTES = 512 * 1024


class SkinFrameCache:
    """Chỉ đọc PNG cục bộ có kích thước hữu hạn; không mạng, không thread riêng mỗi skin."""

    def __init__(self) -> None:
        self._frames: OrderedDict[tuple[str, int, int, bool, int], QImage] = OrderedDict()
        self._meshes: OrderedDict[tuple[str, int, int, bool], tuple[SkinSurface, ...]] = (
            OrderedDict()
        )
        self._lock = threading.Lock()
        self._fallback: QImage | None = None

    def render(self, source: str, slim: bool, frame_index: int) -> QImage:
        """Gọi ở worker; texture cục bộ và hình học đã cache không nạp lại theo từng góc."""
        try:
            source_url = QUrl(source)
            if not source_url.isLocalFile():
                raise ValueError("skin preview requires a local texture")
            path = Path(source_url.toLocalFile())
            stamp = path.stat()
            if stamp.st_size > MAX_TEXTURE_BYTES:
                raise ValueError("skin texture exceeds preview limit")
            frame_index %= FRAME_COUNT
            signature = (str(path), stamp.st_mtime_ns, stamp.st_size, slim)
            key = (*signature, frame_index)
            with self._lock:
                if key in self._frames:
                    self._frames.move_to_end(key)
                    return self._frames[key]
                if signature not in self._meshes:
                    reader = QImageReader(str(path), b"png")
                    dimensions = reader.size()
                    if (
                        dimensions.width() < 64
                        or dimensions.width() > 1024
                        or dimensions.width() % 64
                        or dimensions.height() not in (dimensions.width(), dimensions.width() // 2)
                    ):
                        raise ValueError("unsupported Minecraft skin dimensions")
                    image = reader.read()
                    if image.isNull():
                        raise ValueError("cannot decode skin texture")
                    self._meshes[signature] = skin_surfaces(normalize_skin(image), slim)
                    if len(self._meshes) > MAX_MESH_CACHE:
                        self._meshes.popitem(last=False)
                self._meshes.move_to_end(signature)
                result = render_skin(self._meshes[signature], frame_index)
                self._frames[key] = result
                if len(self._frames) > MAX_FRAME_CACHE:
                    self._frames.popitem(last=False)
                return result
        except (KeyError, OSError, ValueError):
            # Skin hỏng không gây cảnh báo QML/treo thư viện; render skin mặc định đóng kèm.
            with self._lock:
                if self._fallback is None:
                    fallback = QImage(
                        str(Path(__file__).resolve().parents[1] / "skin" / "defaults" / "steve.png")
                    )
                    self._fallback = render_skin(skin_surfaces(normalize_skin(fallback), False), 6)
                return self._fallback
