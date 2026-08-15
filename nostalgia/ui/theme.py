"""Bảng màu và tiện ích vẽ cho phong cách Aero Glass (Windows Vista/7)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QLinearGradient, QPixmap

# ---------- màu ----------
# Kính tối, ám xanh lạnh — Aero luôn lệch về phía lam chứ không xám trung tính.
GLASS_TINT = QColor(20, 32, 50, 120)
GLASS_TINT_STRONG = QColor(14, 24, 40, 158)

# Viền vát: sáng ở cạnh trên, tối ở cạnh dưới -> tạo cảm giác tấm kính dày.
BEVEL_LIGHT = QColor(255, 255, 255, 130)
BEVEL_DARK = QColor(0, 0, 0, 90)

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
    """Segoe UI là font của Aero; trên Linux lấy bản thay thế gần nhất."""
    available = set(QFontDatabase.families())
    for name in ("Segoe UI", "Selawik", "Noto Sans", "Open Sans", "DejaVu Sans"):
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
    g = QLinearGradient(QPointF(0, 0), QPointF(0, height))
    a = lambda v: int(v * strength)  # noqa: E731
    g.setColorAt(0.00, QColor(255, 255, 255, a(120)))
    g.setColorAt(0.46, QColor(255, 255, 255, a(46)))
    g.setColorAt(0.4999, QColor(255, 255, 255, a(38)))
    g.setColorAt(0.50, QColor(255, 255, 255, a(2)))
    g.setColorAt(0.94, QColor(255, 255, 255, a(20)))
    g.setColorAt(1.00, QColor(255, 255, 255, a(34)))
    return g


def sheen_gradient(width: float, strength: float = 1.0) -> QLinearGradient:
    """Ánh sáng hắt ngang, dùng cho tấm kính cao.

    Vệt cắt-giữa chỉ đúng với thanh ngang thấp (caption bar, nút). Áp nó lên một
    panel cao 600px thì thành đường nối ngang giữa màn hình, không phải mặt kính.
    """
    g = QLinearGradient(QPointF(0, 0), QPointF(width, 0))
    a = lambda v: int(v * strength)  # noqa: E731
    g.setColorAt(0.00, QColor(255, 255, 255, a(46)))
    g.setColorAt(0.30, QColor(255, 255, 255, a(18)))
    g.setColorAt(1.00, QColor(255, 255, 255, a(6)))
    return g


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
    return small.scaled(src.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
