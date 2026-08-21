"""Bảng màu và tiện ích vẽ cho phong cách Aero Glass (Windows Vista/7)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter, QPixmap,
)
from PySide6.QtCore import Qt, QPointF

_FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"


def load_bundled_fonts() -> None:
    """Nạp Selawik — bản open-source thay Segoe UI của Windows 7 — đóng gói kèm,
    để giao diện có đúng font thời Aero trên MỌI máy (Linux/macOS không có Segoe
    UI). ui_font() đã ưu tiên 'Selawik' nên sau khi nạp là tự dùng. Gọi một lần
    sau khi tạo QApplication."""
    for ttf in ("selawk.ttf", "selawkb.ttf"):
        p = _FONTS_DIR / ttf
        if p.exists():
            QFontDatabase.addApplicationFont(str(p))

# ---------- màu ----------
# Sắc kính Aero: xanh lam lạnh, khá trong — Windows 7 để màu sau kính ánh lên rõ.
# Tint nhẹ đi để nhìn xuyên kính rõ hơn (trong hơn), bù lại tăng bevel + phản chiếu.
GLASS_TINT = QColor(46, 82, 128, 44)
GLASS_TINT_STRONG = QColor(32, 62, 104, 70)
AERO_TINT = QColor(70, 116, 170, 82)   # dùng cho các thẻ trên dashboard

# Viền vát: sáng ở cạnh trên, tối ở cạnh dưới -> tạo cảm giác tấm kính dày.
BEVEL_LIGHT = QColor(255, 255, 255, 175)
BEVEL_DARK = QColor(0, 0, 0, 96)

TEXT = QColor(238, 244, 250)
TEXT_DIM = QColor(165, 182, 199)
TEXT_FAINT = QColor(120, 137, 155)

# Xanh cỏ cho nút CHƠI, dựng theo kiểu nút Aero: nửa trên sáng, nửa dưới đậm.
GREEN_TOP = QColor(126, 214, 146)
GREEN_MID = QColor(78, 168, 98)
GREEN_LOW = QColor(58, 138, 76)
GREEN_BOT = QColor(86, 180, 108)
GREEN_EDGE = QColor(34, 84, 46)
GREEN_GLOW = QColor(140, 235, 165)

ACCENT = QColor(108, 196, 128)
CONNECTED = QColor(96, 208, 122)
DEGRADED = QColor(226, 178, 74)   # demo / offline đã hạ cấp
DISCONNECTED = QColor(150, 158, 168)


def ui_font(size: int = 10, bold: bool = False) -> QFont:
    """Segoe UI là font của Aero; nơi nào không có thì lấy bản thay thế gần nhất.

    Windows có sẵn Segoe UI nên trúng ngay từ đầu danh sách. macOS không có font
    nào trong nhóm Linux, nên phải chốt hậu bằng Helvetica Neue và Lucida Grande —
    chính là hai font hệ thống của thời Mac cùng thế hệ với Aero.
    """
    available = set(QFontDatabase.families())
    for name in ("Segoe UI", "Selawik", "Noto Sans", "Open Sans", "DejaVu Sans",
                 "Helvetica Neue", "Lucida Grande"):
        if name in available:
            f = QFont(name, size)
            break
    else:
        f = QFont()
        f.setPointSize(size)
    f.setBold(bold)
    f.setHintingPreference(QFont.PreferFullHinting)
    return f


def gloss_gradient(height: float, strength: float = 1.0) -> QLinearGradient:
    """Vệt bóng đặc trưng nhất của Aero: sáng dần rồi *cắt phựt* ở giữa tấm kính.

    Chính điểm dừng đột ngột ở 50% tạo ra cảm giác ánh sáng phản trên mặt kính;
    nếu chuyển mượt suốt chiều cao thì mất ngay chất Vista/7.
    """
    # Bỏ dải cắt-giữa: chỉ giữ ánh sáng dịu ở đỉnh rồi tắt dần, không còn
    # vệt sáng kết thúc ngang giữa panel.
    g = QLinearGradient(QPointF(0, 0), QPointF(0, height))
    a = lambda v: int(min(255, v * strength))  # noqa: E731
    g.setColorAt(0.00, QColor(255, 255, 255, a(120)))
    g.setColorAt(0.10, QColor(255, 255, 255, a(46)))
    g.setColorAt(0.34, QColor(255, 255, 255, a(9)))
    g.setColorAt(1.00, QColor(255, 255, 255, a(4)))
    return g


def glass_reflection(height: float) -> QLinearGradient:
    """Quầng phản chiếu hắt lên từ đáy tấm kính — thêm chiều sâu kiểu Vista/7.

    Ánh sáng dịu màu lam-trắng dâng từ mép dưới rồi tắt dần lên giữa, làm mặt
    kính như có đáy cong hứng sáng chứ không phẳng lì.
    """
    g = QLinearGradient(QPointF(0, height), QPointF(0, height * 0.55))
    g.setColorAt(0.00, QColor(202, 226, 255, 34))
    g.setColorAt(1.00, QColor(202, 226, 255, 0))
    return g


def diagonal_streak(width: float, height: float, strength: float = 1.0) -> QLinearGradient:
    """Vệt sáng xiên giả phản chiếu, port từ bản web (linear-gradient 105°).

    Một dải sáng hẹp chạy chéo qua mặt kính — thứ khiến tấm kính trông như đang
    hắt một nguồn sáng ở xa, chứ không chỉ sáng đều. Giữ hẹp và mờ, quá tay là rẻ.
    """
    # Hướng ~105°: từ trên-trái xuống dưới-phải, lệch nhẹ.
    g = QLinearGradient(QPointF(0, 0), QPointF(width, height * 1.2))
    a = lambda v: int(max(0, min(255, v * strength)))  # noqa: E731
    g.setColorAt(0.00, QColor(255, 255, 255, 0))
    g.setColorAt(0.42, QColor(255, 255, 255, 0))
    g.setColorAt(0.50, QColor(255, 255, 255, a(60)))   # đỉnh vệt sáng
    g.setColorAt(0.58, QColor(255, 255, 255, 0))
    g.setColorAt(1.00, QColor(255, 255, 255, 0))
    return g


def sheen_gradient(width: float, strength: float = 1.0) -> QLinearGradient:
    """Ánh sáng hắt ngang, dùng cho tấm kính cao.

    Vệt cắt-giữa chỉ đúng với thanh ngang thấp (caption bar, nút). Áp nó lên một
    panel cao 600px thì thành đường nối ngang giữa màn hình, không phải mặt kính.
    """
    g = QLinearGradient(QPointF(0, 0), QPointF(width, 0))
    a = lambda v: int(min(255, v * strength))  # noqa: E731
    g.setColorAt(0.00, QColor(255, 255, 255, a(60)))
    g.setColorAt(0.28, QColor(255, 255, 255, a(22)))
    g.setColorAt(1.00, QColor(255, 255, 255, a(7)))
    return g


_NOISE: QPixmap | None = None


def noise_tile() -> QPixmap:
    """Ô nhiễu hạt để lát lên mặt kính — chính là 'noise layer' của material Acrylic/
    Aero thật, thứ làm kính có hạt lấm tấm mịn thay vì phẳng lì.

    Tạo một lần bằng seed cố định để mỗi lần chạy đều giống nhau.
    """
    global _NOISE
    if _NOISE is None:
        import random
        n = 110
        img = QImage(n, n, QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        rnd = random.Random(1971)  # năm... đùa thôi, chỉ cần cố định
        for y in range(n):
            for x in range(n):
                v = rnd.randint(150, 255)
                img.setPixelColor(x, y, QColor(v, v, v, 16))
        _NOISE = QPixmap.fromImage(img)
    return _NOISE


def blur_pixmap(src: QPixmap, factor: int = 12, passes: int = 2) -> QPixmap:
    """Làm mờ bằng cách thu nhỏ rồi phóng to với nội suy mượt.

    Rẻ hơn QGraphicsBlurEffect nhiều lần và với kính mờ thì kết quả nhìn như nhau.
    """
    if src.isNull():
        return src
    w, h = max(1, src.width() // factor), max(1, src.height() // factor)
    small = src.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    for _ in range(passes - 1):
        small = small.scaled(
            max(1, w // 2), max(1, h // 2), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
    blurred = small.scaled(src.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    # Lớp "Aero": chồng chính nó ở chế độ Overlay để đẩy tương phản + bão hoà,
    # thêm chút sáng — đúng cách Windows 7 làm màu sau kính rực hơn thực tế.
    out = QPixmap(blurred.size())
    p = QPainter(out)
    p.drawPixmap(0, 0, blurred)
    p.setCompositionMode(QPainter.CompositionMode_Overlay)
    p.setOpacity(0.5)
    p.drawPixmap(0, 0, blurred)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.setOpacity(0.10)
    p.fillRect(out.rect(), QColor(255, 255, 255))   # sáng nhẹ toàn khung
    p.end()
    return out
