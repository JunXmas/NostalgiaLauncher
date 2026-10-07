"""Chuẩn hoá ảnh chia sẻ và cache skin công khai; không thay đổi skin Minecraft gốc."""

import base64
import hashlib
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QUrl
from PySide6.QtGui import QImage, QImageReader, QPainter

from nostalgia.errors import SocialError
from nostalgia.ui.skin_mesh import normalize_skin
from nostalgia.ui.skin_sprite import save_image


def encode_png(image: QImage) -> str:
    payload = QByteArray()
    stream = QBuffer(payload)
    stream.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(stream, "PNG"):  # type: ignore[call-overload] # PySide accepts str at runtime.
        raise SocialError("Không đọc được ảnh skin.")
    return base64.b64encode(payload.data()).decode()


def publish_skin(source: str) -> tuple[str, str]:
    url = QUrl(source)
    if not url.isLocalFile():
        raise SocialError("Chỉ chia sẻ skin trong thư viện launcher.")
    path = Path(url.toLocalFile())
    if path.stat().st_size > 512_000:
        raise SocialError("Skin vượt giới hạn kích thước.")
    reader = QImageReader(str(path), b"png")
    dimensions = reader.size()
    if dimensions.width() not in range(64, 1025, 64) or dimensions.height() not in (
        dimensions.width(),
        dimensions.width() // 2,
    ):
        raise SocialError("Kích thước skin không hợp lệ.")
    image = reader.read()
    if image.isNull():
        raise SocialError("Không đọc được PNG skin.")
    normalized = normalize_skin(image).convertToFormat(QImage.Format.Format_ARGB32)
    head = normalized.copy(8, 8, 8, 8)
    painter = QPainter(head)
    painter.drawImage(0, 0, normalized.copy(40, 8, 8, 8))
    painter.end()
    return encode_png(normalized), encode_png(head)


def cache_skin(cache_dir: Path, encoded: str) -> str:
    if not encoded:
        return ""
    payload = base64.b64decode(encoded, validate=True)
    image = QImage.fromData(payload)
    if image.isNull() or image.width() != 64 or image.height() != 64:
        raise SocialError("Skin chia sẻ bị hỏng.")
    digest = hashlib.sha256(payload).hexdigest()
    path = cache_dir / (digest + ".png")
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        save_image(image, path)
    for stale in sorted(cache_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[
        48:
    ]:
        if stale != path:
            stale.unlink(missing_ok=True)
    return QUrl.fromLocalFile(str(path)).toString()
