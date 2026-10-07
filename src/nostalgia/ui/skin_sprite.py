"""Thumbnail và atlas skin 3D cache trên đĩa; atlas 1536x1536 nằm dưới giới hạn GPU cũ."""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QPainter

from nostalgia.ui.skin_frame_cache import SkinFrameCache
from nostalgia.ui.skin_renderer import FRAME_COUNT, FRAME_HEIGHT, FRAME_WIDTH

ATLAS_COLUMNS = 12
MAX_DISK_BYTES = 64 * 1024 * 1024
RENDER_REVISION = 1


@dataclass(frozen=True, slots=True)
class SkinPreview:
    thumbnail: Path
    atlas: Path | None


def save_image(image: QImage, target: Path) -> None:
    """Ghi nguyên tử; hai cửa sổ cùng dựng skin không thấy PNG đang ghi dở."""
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".png", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        if not image.save(str(temporary_path)):
            raise OSError("cannot write skin preview")
        temporary_path.replace(target)
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_skin_preview(
    cache_dir: Path,
    renderer: SkinFrameCache,
    source: str,
    slim: bool,
    revision: str,
    animated: bool,
) -> SkinPreview:
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        stamp = Path(QUrl(source).toLocalFile()).stat().st_mtime_ns
    except OSError:
        stamp = 0
    digest = hashlib.sha256(
        f"{RENDER_REVISION}|{source}|{slim}|{revision}|{stamp}".encode()
    ).hexdigest()
    thumbnail = cache_dir / f"{digest}-thumb.png"
    atlas = cache_dir / f"{digest}-atlas.png" if animated else None
    if not thumbnail.is_file():
        save_image(renderer.render(source, slim, 5), thumbnail)
    if atlas is not None and not atlas.is_file():
        image = QImage(
            FRAME_WIDTH * ATLAS_COLUMNS,
            FRAME_HEIGHT * (FRAME_COUNT // ATLAS_COLUMNS),
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        for frame_index in range(FRAME_COUNT):
            painter.drawImage(
                (frame_index % ATLAS_COLUMNS) * FRAME_WIDTH,
                (frame_index // ATLAS_COLUMNS) * FRAME_HEIGHT,
                renderer.render(source, slim, frame_index),
            )
        painter.end()
        save_image(image, atlas)
    return SkinPreview(thumbnail, atlas)


def prune_skin_previews(cache_dir: Path, protected: frozenset[Path]) -> None:
    """Chỉ xoá ảnh trong cache renderer; không chạm PNG skin gốc của người chơi."""
    photos = sorted(cache_dir.glob("*.png"), key=lambda path: path.stat().st_mtime_ns)
    total = sum(path.stat().st_size for path in photos)
    for path in photos:
        if total <= MAX_DISK_BYTES:
            break
        if path not in protected:
            total -= path.stat().st_size
            path.unlink(missing_ok=True)
