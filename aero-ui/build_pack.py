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


def _a(color: QColor, alpha: int) -> QColor:
    c = QColor(color); c.setAlpha(max(0, min(255, alpha))); return c


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
    dis = state == "disabled"

    # Thân kính: gradient dọc SÂU hơn — đỉnh sáng, giữa hơi thắt tối (bụng kính),
    # đáy sáng nhẹ lại cho cảm giác dày.
    base = QLinearGradient(0, 0, 0, BTN_H)
    base.setColorAt(0.0, _a(tint.lighter(126), min(255, a + 46)))
    base.setColorAt(0.5, _a(tint.darker(104), a))
    base.setColorAt(0.52, _a(tint.darker(116), min(255, a + 10)))
    base.setColorAt(1.0, _a(tint.darker(120), min(255, a + 16)))
    p.fillRect(QRectF(0, 0, BTN_W, BTN_H), base)

    # Gloss trên: dải phản chiếu CRISP ở 1/2 trên, tắt gọn ở giữa.
    hi = 150 if state == "hover" else (124 if state == "normal" else 58)
    gloss = QLinearGradient(0, 0, 0, BTN_H)
    gloss.setColorAt(0.0, QColor(255, 255, 255, hi))
    gloss.setColorAt(0.38, QColor(255, 255, 255, int(hi * 0.32)))
    gloss.setColorAt(0.5, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, BTN_W, BTN_H * 0.5), gloss)

    # Phản chiếu đáy: quầng xanh-trắng dịu hắt lên từ mép dưới (glass reflection).
    refl = QLinearGradient(0, BTN_H * 0.68, 0, BTN_H)
    refl.setColorAt(0.0, QColor(190, 222, 255, 0))
    refl.setColorAt(1.0, QColor(200, 228, 255, 0 if dis else 40))
    p.fillRect(QRectF(0, BTN_H * 0.68, BTN_W, BTN_H * 0.32), refl)

    # Vạch sáng sát đỉnh + mép đáy tối → khối lồi, chiều sâu.
    p.fillRect(QRectF(1, 1, BTN_W - 2, 1), QColor(255, 255, 255, 210 if not dis else 90))
    p.fillRect(QRectF(1, BTN_H - 2, BTN_W - 2, 1), QColor(0, 0, 0, 130))
    p.restore()

    # Viền kép: ngoài tối tách nền, trong sáng cho ánh kính.
    p.setBrush(Qt.NoBrush)
    p.setPen(QColor(0, 0, 0, 96)); p.drawPath(path)
    inner = QPainterPath()
    inner.addRoundedRect(QRectF(1.5, 1.5, BTN_W - 3, BTN_H - 3), RADIUS - 1, RADIUS - 1)
    p.setPen(QColor(255, 255, 255, 110 if not dis else 44)); p.drawPath(inner)
    p.end()
    return img


def _glass_body(p, w, h, tint, a, radius):
    """Thân kính bo góc + gloss nửa trên + vạch sáng đỉnh + mép đáy tối."""
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
    p.save(); p.setClipPath(path)
    base = QLinearGradient(0, 0, 0, h)
    base.setColorAt(0.0, _a(tint.lighter(126), min(255, a + 46)))
    base.setColorAt(0.5, _a(tint.darker(104), a))
    base.setColorAt(1.0, _a(tint.darker(120), min(255, a + 16)))
    p.fillRect(QRectF(0, 0, w, h), base)
    gloss = QLinearGradient(0, 0, 0, h)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 150))
    gloss.setColorAt(0.4, QColor(255, 255, 255, 48))
    gloss.setColorAt(0.5, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, w, h * 0.5), gloss)
    refl = QLinearGradient(0, h * 0.68, 0, h)
    refl.setColorAt(0.0, QColor(200, 228, 255, 0)); refl.setColorAt(1.0, QColor(200, 228, 255, 44))
    p.fillRect(QRectF(0, h * 0.68, w, h * 0.32), refl)
    p.fillRect(QRectF(1, 1, w - 2, 1), QColor(255, 255, 255, 210))
    p.fillRect(QRectF(1, h - 2, w - 2, 1), QColor(0, 0, 0, 130))
    p.restore()
    p.setBrush(Qt.NoBrush)
    p.setPen(QColor(0, 0, 0, 96)); p.drawPath(path)


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
    g.setColorAt(0, _a(tint.lighter(124), min(255, a + 40)))
    g.setColorAt(0.5, _a(tint.darker(104), a))
    g.setColorAt(1, _a(tint.darker(120), min(255, a + 12)))
    p.fillRect(QRectF(0, 0, w, h), g)
    gl = QLinearGradient(0, 0, 0, h * 0.5)
    gl.setColorAt(0, QColor(255, 255, 255, 132 if selected else 104))
    gl.setColorAt(0.4, QColor(255, 255, 255, 40)); gl.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, w, h * 0.5), gl)
    p.fillRect(QRectF(2, 1, w - 4, 1), QColor(255, 255, 255, 200))
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


WALLPAPER = ROOT / "wallpaper.png"   # ảnh Aero GỐC (vẽ bằng make_wallpaper.py)

def build_edition(text: str = "NOSTALGIA EDITION") -> None:
    """Thay chữ 'JAVA EDITION' dưới logo bằng text khác (gui/title/edition.png).

    Vẽ text nhỏ (không khử răng cưa) rồi PHÓNG TO nearest -> ra khối pixel giống
    phông edition của Minecraft. Xuất 512×64 (tỉ lệ 8:1 như bản gốc); game tự co
    giãn nên phủ mọi phiên bản qua cùng một path.
    """
    from PySide6.QtGui import QFont, QFontMetrics
    base = QFont("monospace"); base.setBold(True); base.setPixelSize(16)
    fm = QFontMetrics(base)
    tw, th = fm.horizontalAdvance(text) + 4, fm.height() + 4
    small = QImage(tw, th, QImage.Format_ARGB32); small.fill(Qt.transparent)
    p = QPainter(small); p.setFont(base)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setRenderHint(QPainter.TextAntialiasing, False)
    y = fm.ascent() + 1
    p.setPen(QColor(28, 30, 34, 210)); p.drawText(2, y + 1, text)   # bóng đổ
    p.setPen(QColor(214, 219, 226)); p.drawText(1, y, text)         # chữ xám sáng
    p.end()
    big = small.scaled(512, 64, Qt.IgnoreAspectRatio, Qt.FastTransformation)
    write_png(big, GUI / "title" / "edition.png")


def build_panorama() -> None:
    """Thay panorama title screen bằng wallpaper Aero (xoay chậm sau menu chính).

    Đường dẫn `gui/title/background/panorama_*` giống nhau từ 1.8→26.x nên một bộ
    phủ mọi phiên bản. 4 mặt tường = ảnh (fill vuông), trần/sàn = gradient xanh
    mượt lấy màu từ ảnh, tránh vệt sáng vắt lên 'trần' trông kỳ.
    """
    src = QImage(str(WALLPAPER))
    if src.isNull():
        print("  (skip panorama: no wallpaper.jpg)")
        return
    dest = GUI / "title" / "background"
    S = 512
    # 6 mặt panorama = màu XANH PHẲNG (gradient nhẹ), lấy tông từ ảnh. Đồng đều
    # nên vòng xoay không lộ gì — không còn "panorama", chỉ là nền tĩnh.
    top = src.pixelColor(src.width() // 2, 4)
    bot = src.pixelColor(src.width() // 2, src.height() - 4)

    def flat(c1, c2):
        img = QImage(S, S, QImage.Format_ARGB32)
        g = QLinearGradient(0, 0, 0, S); g.setColorAt(0, c1); g.setColorAt(1, c2)
        p = QPainter(img); p.fillRect(0, 0, S, S, g); p.end()
        return img

    for i in range(6):
        write_png(flat(top, bot), dest / f"panorama_{i}.png")

    # panorama_overlay: tấm ảnh 2D vẽ PHẲNG, đè kín — chính là "ảnh đơn thuần".
    # Full-res + đục hẳn cho nét nhất có thể (bản cũ vẫn bị Minecraft blur skybox).
    ov = src.scaled(1920, 1200, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    ov = ov.convertToFormat(QImage.Format_ARGB32)
    solid = QImage(ov.size(), QImage.Format_ARGB32); solid.fill(Qt.black)
    pp = QPainter(solid); pp.drawImage(0, 0, ov); pp.end()
    write_png(solid, dest / "panorama_overlay.png")


def _flat_tile(base: QColor, alpha: int, size: int = 16) -> QImage:
    """Ô tint kính Aero PHẲNG (một màu, một alpha) để game tile kín màn hình.

    Phải phẳng: tile lặp mỗi `size` px nên bất kỳ gradient/nhiễu nào cũng lộ mạch
    lưới. Blur là do vanilla lo (menuBackgroundBlurriness); ô này chỉ nhuộm màu.
    """
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(_a(base, alpha))
    return img


def build_glass_background() -> None:
    """Nền menu = kính Aero mờ (1.20.5+).

    Từ 1.20.5 Minecraft đã BLUR sẵn thế giới sau mỗi màn hình; ta chỉ phủ một
    lớp tint xanh Aero translucent lên trên -> ra 'frosted acrylic'. Ba texture:
      • inworld_menu_background      — phủ toàn màn khi mở menu lúc đang trong game
      • inworld_menu_list_background — vùng danh sách (đậm hơn cho dễ đọc)
      • menu_list_background         — khi KHÔNG có world phía sau (đè lên panorama)
    Bản cũ không có các path này thì bỏ qua êm — không ảnh hưởng.
    """
    # Translucent để world (đã blur trên GPU thật / bởi mod Blur+) hiện xuyên qua
    # = kính mờ Aero. Alpha đủ cao để thành một "tấm kính" rõ và chữ trắng đọc tốt
    # kể cả khi blur bị tắt, nhưng vẫn thấy cảnh phía sau.
    aero = QColor(22, 48, 86)          # xanh Aero
    write_png(_flat_tile(aero, 125), GUI / "inworld_menu_background.png")
    write_png(_flat_tile(QColor(12, 28, 52), 150),
              GUI / "inworld_menu_list_background.png")
    write_png(_flat_tile(aero, 120), GUI / "menu_list_background.png")


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
    build_glass_background()  # nền menu kính mờ (1.20.5+)
    build_panorama() # wallpaper title screen (mọi phiên bản)
    build_edition()  # "NOSTALGIA EDITION" thay "JAVA EDITION"
    build_meta()
    build_preview()  # ảnh xem trước -> aero-ui/preview.png (không ship)
    # build_legacy() KHÔNG chạy: widgets.png được ghép lúc cài từ jar người dùng.
    print("Aero pack (modern, shipped) -> ", PACK)


if __name__ == "__main__":
    main()
