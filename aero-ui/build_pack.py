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
PACK = ROOT / "aero-pack"
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


def paint_button(state: str) -> QImage:
    """Một thanh nút kính 200×20: nền xanh mờ + gloss dọc + bevel trên/dưới.

    Đồng đều theo chiều ngang (nút vanilla lấy mép trái/phải từ texture nên phải
    tránh vân dọc), gradient theo chiều dọc để ra ánh kính.
    """
    img = QImage(BTN_W, BTN_H, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    tint = TINTS[state]
    a = ALPHA[state]
    r = QRectF(0.5, 0.5, BTN_W - 1, BTN_H - 1)

    # Nền kính: gradient dọc, trên sáng hơn đáy.
    base = QLinearGradient(0, 0, 0, BTN_H)
    top = QColor(tint); top.setAlpha(min(255, a + 26))
    bot = QColor(tint.darker(122)); bot.setAlpha(a)
    base.setColorAt(0.0, top)
    base.setColorAt(1.0, bot)
    p.fillRect(r, base)

    # Gloss: nửa trên phủ trắng mờ rồi tắt dần ở giữa.
    gloss = QLinearGradient(0, 0, 0, BTN_H)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 96 if state != "disabled" else 40))
    gloss.setColorAt(0.48, QColor(255, 255, 255, 18))
    gloss.setColorAt(0.5, QColor(255, 255, 255, 0))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, BTN_W, BTN_H), gloss)

    # Bevel trên sáng + mép dưới tối, cho cảm giác lồi.
    p.fillRect(QRectF(0, 0, BTN_W, 1), QColor(255, 255, 255, 150))
    p.fillRect(QRectF(0, BTN_H - 1, BTN_W, 1), QColor(0, 0, 0, 96))

    # Viền mảnh để nút tách khỏi nền.
    p.setPen(QColor(255, 255, 255, 70))
    p.drawRect(r)
    p.end()
    return img


def write_png(img: QImage, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), "PNG")


def build_modern() -> None:
    """Sprite rời cho 1.20.2+, kèm .mcmeta khai báo 9-slice (border 3)."""
    sprites = GUI / "sprites" / "widget"
    mapping = {"button": "normal", "button_highlighted": "hover",
               "button_disabled": "disabled"}
    meta = {"gui": {"scaling": {"type": "nine_slice",
                                "width": BTN_W, "height": BTN_H, "border": 3}}}
    for name, state in mapping.items():
        write_png(paint_button(state), sprites / f"{name}.png")
        (sprites / f"{name}.png.mcmeta").write_text(json.dumps(meta, indent=2))


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
    """Ảnh xem trước 3 nút trên nền tối, để soi mà không cần mở game."""
    W, H = 260, 150
    canvas = QImage(W, H, QImage.Format_ARGB32)
    bg = QLinearGradient(0, 0, 0, H)
    bg.setColorAt(0, QColor(40, 58, 46)); bg.setColorAt(1, QColor(18, 26, 20))
    pc = QPainter(canvas); pc.fillRect(0, 0, W, H, bg)
    for i, state in enumerate(("normal", "hover", "disabled")):
        pc.drawImage(30, 20 + i * 42, paint_button(state))
    pc.end()
    write_png(canvas, ROOT / "preview.png")


def main() -> None:
    QApplication([])
    build_modern()
    build_legacy()
    build_meta()
    build_preview()
    print("Aero pack -> ", PACK)


if __name__ == "__main__":
    main()
