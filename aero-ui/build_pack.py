"""Dựng Aero UI resource pack — biến nút/khung của Minecraft thành kính Aero.

Một pack DUY NHẤT phủ hai thời kỳ GUI:
  • ≤1.19.x  -> assets/minecraft/textures/gui/widgets.png   (atlas, gồm 1.12.2)
  • 1.20.2+  -> assets/minecraft/textures/gui/sprites/widget/*.png (+ .mcmeta, 9-slice)

Vẽ bằng QPainter theo đúng thẩm mỹ kính của launcher, nên nút trong game ăn khớp
với nút trên launcher. Chạy:  python aero-ui/build_pack.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent
# Pack SHIPPED cùng launcher (chỉ sprite modern, 100% của mình). Nằm dưới
# ui/assets nên được PyInstaller đóng gói sẵn. Legacy widgets.png KHÔNG ship —
# nó được ghép lúc cài từ jar của chính người dùng (xem nostalgia/aero.py).
PACK = ROOT.parent / "nostalgia" / "ui" / "assets" / "aero-pack"
GUI = PACK / "assets" / "minecraft" / "textures" / "gui"
VANILLA_WIDGETS = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT / "vanilla" / "widgets.png")

BTN_W, BTN_H = 200, 20

# Bảng màu kính Aero (xanh Windows 7), theo trạng thái nút.
TINTS = {
    "normal":   QColor(74, 126, 186),
    "hover":    QColor(104, 168, 226),
    "disabled": QColor(120, 130, 146),
}
ALPHA = {"normal": 150, "hover": 176, "disabled": 96}


RADIUS = 4.0   # bo góc (px); ≤ border của 9-slice để bản mới không kéo méo góc

def paint_button(state: str) -> QImage:
    """Một nút kính Aero 200×20 BO GÓC — theo đúng công thức nút của launcher:
    thân kính xanh trong, gloss nửa trên, vạch sáng đỉnh, mép đáy tối, viền bo mềm.

    Ngoài vùng bo góc để TRONG SUỐT nên góc nút lộ nền phía sau → cảm giác kính
    thật. Đồng đều theo chiều ngang (nút vanilla/9-slice kéo giãn ngang).
    """
    img = QImage(BTN_W, BTN_H, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    tint = TINTS[state]
    a = ALPHA[state]

    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.5, 0.5, BTN_W - 1, BTN_H - 1), RADIUS, RADIUS)

    p.save()
    p.setClipPath(path)   # mọi thứ vẽ ra đều nằm trong hình bo góc

    # Thân kính: gradient dọc, trên sáng hơn đáy.
    base = QLinearGradient(0, 0, 0, BTN_H)
    top = QColor(tint.lighter(118)); top.setAlpha(min(255, a + 34))
    mid = QColor(tint); mid.setAlpha(a)
    bot = QColor(tint.darker(126)); bot.setAlpha(min(255, a + 8))
    base.setColorAt(0.0, top)
    base.setColorAt(0.5, mid)
    base.setColorAt(1.0, bot)
    p.fillRect(QRectF(0, 0, BTN_W, BTN_H), base)

    # Gloss nửa trên: trắng đậm ở đỉnh, tắt hẳn ở giữa (ánh kính Aero).
    hi = 132 if state == "hover" else (108 if state == "normal" else 52)
    gloss = QLinearGradient(0, 0, 0, BTN_H)
    gloss.setColorAt(0.0, QColor(255, 255, 255, hi))
    gloss.setColorAt(0.46, QColor(255, 255, 255, 22))
    gloss.setColorAt(0.5, QColor(255, 255, 255, 0))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, BTN_W, BTN_H), gloss)

    # Vạch sáng sát đỉnh + mép đáy tối → cảm giác lồi, có chiều sâu.
    p.fillRect(QRectF(1, 1, BTN_W - 2, 1), QColor(255, 255, 255, 190))
    p.fillRect(QRectF(1, BTN_H - 2, BTN_W - 2, 1), QColor(0, 0, 0, 120))
    p.restore()

    # Viền bo góc: ngoài tối nhẹ cho tách nền, trong sáng cho ánh kính.
    p.setBrush(Qt.NoBrush)
    p.setPen(QColor(0, 0, 0, 90))
    p.drawPath(path)
    inner = QPainterPath()
    inner.addRoundedRect(QRectF(1.5, 1.5, BTN_W - 3, BTN_H - 3), RADIUS - 1, RADIUS - 1)
    p.setPen(QColor(255, 255, 255, 96 if state != "disabled" else 40))
    p.drawPath(inner)
    p.end()
    return img


def _glass_body(p, w, h, tint, a, radius):
    """Thân kính bo góc + gloss nửa trên + vạch sáng đỉnh + mép đáy tối."""
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
    p.save(); p.setClipPath(path)
    base = QLinearGradient(0, 0, 0, h)
    top = QColor(tint.lighter(118)); top.setAlpha(min(255, a + 34))
    mid = QColor(tint); mid.setAlpha(a)
    bot = QColor(tint.darker(126)); bot.setAlpha(min(255, a + 8))
    base.setColorAt(0.0, top); base.setColorAt(0.5, mid); base.setColorAt(1.0, bot)
    p.fillRect(QRectF(0, 0, w, h), base)
    gloss = QLinearGradient(0, 0, 0, h)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 120))
    gloss.setColorAt(0.46, QColor(255, 255, 255, 22))
    gloss.setColorAt(0.5, QColor(255, 255, 255, 0))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, w, h), gloss)
    p.fillRect(QRectF(1, 1, w - 2, 1), QColor(255, 255, 255, 190))
    p.fillRect(QRectF(1, h - 2, w - 2, 1), QColor(0, 0, 0, 120))
    p.restore()
    p.setBrush(Qt.NoBrush)
    p.setPen(QColor(0, 0, 0, 90)); p.drawPath(path)


def paint_slider_track() -> QImage:
    """Rãnh trượt: kính lõm tối, viền trong sáng — cảm giác khắc chìm."""
    w, h = 200, 20
    img = QImage(w, h, QImage.Format_ARGB32); img.fill(Qt.transparent)
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing, True)
    from PySide6.QtGui import QPainterPath
    path = QPainterPath(); path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 4, 4)
    p.setClipPath(path)
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0.0, QColor(18, 30, 46, 150)); g.setColorAt(1.0, QColor(30, 48, 72, 120))
    p.fillRect(QRectF(0, 0, w, h), g)
    p.fillRect(QRectF(1, 1, w - 2, 1), QColor(0, 0, 0, 120))     # bóng lõm đỉnh
    p.fillRect(QRectF(1, h - 2, w - 2, 1), QColor(255, 255, 255, 60))
    p.setClipping(False); p.setPen(QColor(255, 255, 255, 55)); p.setBrush(Qt.NoBrush)
    p.drawPath(path); p.end()
    return img


def paint_slider_handle(state: str) -> QImage:
    """Núm trượt: viên kính bóng nhỏ."""
    w, h = 8, 20
    img = QImage(w, h, QImage.Format_ARGB32); img.fill(Qt.transparent)
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing, True)
    tint = TINTS["hover" if state == "hover" else "normal"]
    _glass_body(p, w, h, tint, ALPHA["hover"] if state == "hover" else 190, 2.5)
    p.end(); return img


def paint_tab(selected: bool) -> QImage:
    """Tab: panel kính bo góc trên, đáy phẳng để dính vào nội dung."""
    w, h = 130, 24
    img = QImage(w, h, QImage.Format_ARGB32); img.fill(Qt.transparent)
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing, True)
    tint = TINTS["hover"] if selected else TINTS["normal"]
    a = 186 if selected else 130
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(0.5, h); path.lineTo(0.5, 5)
    path.quadTo(0.5, 0.5, 5, 0.5); path.lineTo(w - 5, 0.5)
    path.quadTo(w - 0.5, 0.5, w - 0.5, 5); path.lineTo(w - 0.5, h)
    p.save(); p.setClipPath(path)
    g = QLinearGradient(0, 0, 0, h)
    tp = QColor(tint.lighter(116)); tp.setAlpha(min(255, a + 30))
    bt = QColor(tint.darker(120)); bt.setAlpha(a)
    g.setColorAt(0, tp); g.setColorAt(1, bt)
    p.fillRect(QRectF(0, 0, w, h), g)
    gl = QLinearGradient(0, 0, 0, h)
    gl.setColorAt(0, QColor(255, 255, 255, 110)); gl.setColorAt(0.5, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, w, h), gl)
    p.fillRect(QRectF(2, 1, w - 4, 1), QColor(255, 255, 255, 180))
    p.restore()
    p.setBrush(Qt.NoBrush); p.setPen(QColor(0, 0, 0, 80)); p.drawPath(path)
    p.end(); return img


def write_png(img: QImage, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), "PNG")


def _slice(w, h, border):
    return {"gui": {"scaling": {"type": "nine_slice",
                                "width": w, "height": h, "border": border}}}


def _emit(sprites, name, img, meta):
    write_png(img, sprites / f"{name}.png")
    (sprites / f"{name}.png.mcmeta").write_text(json.dumps(meta, indent=2))


def build_modern() -> None:
    """Bộ sprite ĐẦY ĐỦ cho 1.20.2+ (gồm 1.21.x, 26.x): nút, slider, tab.

    Mỗi sprite tự khai .mcmeta 9-slice riêng (border ≥ bán kính bo) nên launcher
    kiểm soát hoàn toàn, không phụ thuộc kích thước gốc của từng bản.
    """
    sprites = GUI / "sprites" / "widget"
    # Nút (border 5 để chứa góc bo 4px).
    for name, state in {"button": "normal", "button_highlighted": "hover",
                        "button_disabled": "disabled"}.items():
        _emit(sprites, name, paint_button(state), _slice(BTN_W, BTN_H, 5))
    # Thanh trượt: rãnh + núm.
    _emit(sprites, "slider", paint_slider_track(), _slice(200, 20, 4))
    for name, state in {"slider_handle": "normal",
                        "slider_handle_highlighted": "hover"}.items():
        _emit(sprites, name, paint_slider_handle(state),
              _slice(8, 20, {"left": 3, "top": 3, "right": 3, "bottom": 3}))
    # Tab: thường / được chọn / hover (+ chọn&hover).
    for name, sel in {"tab": False, "tab_highlighted": False,
                      "tab_selected": True, "tab_selected_highlighted": True}.items():
        _emit(sprites, name, paint_tab(sel),
              _slice(130, 24, {"left": 5, "top": 5, "right": 5, "bottom": 0}))


def build_legacy() -> None:
    """Sơn 3 vùng nút trong widgets.png gốc, giữ nguyên hotbar và phần khác."""
    base = QImage(str(VANILLA_WIDGETS))
    if base.isNull():
        raise SystemExit(f"Không đọc được widgets.png gốc: {VANILLA_WIDGETS}")
    base = base.convertToFormat(QImage.Format_ARGB32)
    # Toạ độ nút trong widgets.png (256×256): mỗi vùng 200×20.
    regions = {"disabled": 46, "normal": 66, "hover": 86}
    p = QPainter(base)
    for state, y in regions.items():
        p.setCompositionMode(QPainter.CompositionMode_Source)  # thay hẳn pixel
        p.drawImage(0, y, paint_button(state))
    p.end()
    write_png(base, GUI / "widgets.png")


def build_meta() -> None:
    PACK.mkdir(parents=True, exist_ok=True)
    # pack_format 3 để 1.12.2 nạp; supported_formats để bản mới nhận sạch.
    mc = {"pack": {
        "pack_format": 3,
        "supported_formats": {"min_inclusive": 3, "max_inclusive": 99},
        "description": "§bAero glass UI §7— Nostalgia Launcher",
    }}
    (PACK / "pack.mcmeta").write_text(json.dumps(mc, indent=2))
    # Icon pack: một ô kính nhỏ.
    icon = QImage(64, 64, QImage.Format_ARGB32); icon.fill(Qt.transparent)
    p = QPainter(icon); p.setRenderHint(QPainter.Antialiasing, True)
    g = QLinearGradient(0, 0, 0, 64)
    g.setColorAt(0, QColor(120, 180, 235, 235)); g.setColorAt(1, QColor(52, 96, 150, 235))
    p.setPen(QColor(255, 255, 255, 150)); p.setBrush(g)
    p.drawRoundedRect(QRectF(6, 6, 52, 52), 10, 10)
    p.fillRect(QRectF(12, 12, 40, 16), QColor(255, 255, 255, 70))
    p.end()
    write_png(icon, PACK / "pack.png")


def build_preview() -> None:
    """Ảnh xem trước bộ widget Aero trên nền tối, soi mà không cần mở game."""
    W, H = 300, 250
    canvas = QImage(W, H, QImage.Format_ARGB32)
    bg = QLinearGradient(0, 0, 0, H)
    bg.setColorAt(0, QColor(40, 58, 46)); bg.setColorAt(1, QColor(18, 26, 20))
    pc = QPainter(canvas); pc.fillRect(0, 0, W, H, bg)
    pc.setRenderHint(QPainter.SmoothPixmapTransform, True)
    for i, state in enumerate(("normal", "hover", "disabled")):
        pc.drawImage(30, 16 + i * 30, paint_button(state))
    # slider (rãnh + núm) ở giữa
    from PySide6.QtGui import QPixmap
    pc.drawImage(30, 118, paint_slider_track())
    pc.drawImage(30 + 96, 118, paint_slider_handle("hover"))
    # hai tab
    pc.drawImage(30, 150, paint_tab(True))
    pc.drawImage(30, 150, QImage())  # noop giữ layout
    pc.drawImage(166, 152, paint_tab(False))
    pc.end()
    write_png(canvas, ROOT / "preview.png")


def main() -> None:
    QApplication([])
    build_modern()   # sprite modern -> ship trong ui/assets/aero-pack
    build_meta()
    build_preview()  # ảnh xem trước -> aero-ui/preview.png (không ship)
    # build_legacy() KHÔNG chạy: widgets.png được ghép lúc cài từ jar người dùng.
    print("Aero pack (modern, shipped) -> ", PACK)


if __name__ == "__main__":
    main()
