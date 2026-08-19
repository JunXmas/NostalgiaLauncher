"""Cài "Aero UI" resource pack vào một instance — biến nút/slider/tab của
Minecraft thành kính Aero, khớp giao diện launcher.

Một pack phủ hai thời kỳ GUI:
  • 1.20.2+ (gồm 1.21.x, 26.x): dùng thẳng bộ sprite `gui/sprites/widget/*`
    ship kèm launcher (100% của mình).
  • ≤1.20.1 (1.8.9 … 1.20.1): GHÉP nút Aero vào `gui/widgets.png` rút TỪ JAR
    CỦA CHÍNH BẢN ĐÓ lúc cài — đúng từng phiên bản, và không nhét texture gốc
    Mojang vào mã nguồn. Toạ độ nút ổn định 1.8→1.20.1 nên một công thức ghép
    dùng chung cho mọi bản legacy.

Việc chọn modern hay legacy KHÔNG đoán theo tên phiên bản (1.8.9, 26.2, forge…)
mà nhìn thẳng nội dung jar: có `gui/sprites/widget/button.png` -> modern; có
`gui/widgets.png` -> legacy. Nhờ vậy đúng với mọi cách đánh số, kể cả về sau.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

PACK_NAME = "Aero UI.zip"
PACK_DIR = Path(__file__).resolve().parent / "ui" / "assets" / "aero-pack"

SPRITES = "assets/minecraft/textures/gui/sprites/widget"
WIDGETS = "assets/minecraft/textures/gui/widgets.png"
# Toạ độ 3 trạng thái nút trong widgets.png (256×256), mỗi vùng 200×20.
BTN_REGIONS = {"button_disabled.png": 46, "button.png": 66, "button_highlighted.png": 86}


def _legacy_widgets_png(client_jar: Path) -> bytes | None:
    """Rút widgets.png từ jar rồi sơn 3 nút Aero lên, trả về PNG bytes.

    Trả None nếu jar không có widgets.png (tức bản này là hệ sprite -> modern).
    """
    try:
        with zipfile.ZipFile(client_jar) as z:
            if WIDGETS not in z.namelist():
                return None
            base_png = z.read(WIDGETS)
    except (OSError, zipfile.BadZipFile):
        return None

    from PySide6.QtGui import QImage, QPainter  # nạp trễ: CLI không cần Qt
    base = QImage.fromData(base_png, "PNG").convertToFormat(QImage.Format_ARGB32)
    if base.isNull():
        return None
    p = QPainter(base)
    for sprite, y in BTN_REGIONS.items():
        btn = QImage(str(PACK_DIR / SPRITES / sprite))
        if btn.isNull():
            continue
        p.setCompositionMode(QPainter.CompositionMode_Source)  # thay hẳn pixel vùng nút
        p.drawImage(0, y, btn)
    p.end()
    from PySide6.QtCore import QBuffer, QByteArray
    ba = QByteArray(); buf = QBuffer(ba); buf.open(QBuffer.WriteOnly)
    base.save(buf, "PNG"); buf.close()
    return bytes(ba)


def _build_zip(dest: Path, legacy_widgets: bytes | None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PACK_DIR.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(PACK_DIR).as_posix())
        if legacy_widgets is not None:
            z.writestr(WIDGETS, legacy_widgets)


def _enable_in_options(options: Path, modern: bool) -> None:
    """Thêm pack vào resourcePacks trong options.txt (giữ nguyên các dòng khác)."""
    entry = ("file/" if modern else "") + PACK_NAME
    lines = options.read_text().splitlines() if options.exists() else []
    out, found = [], False
    for ln in lines:
        if ln.startswith("resourcePacks:"):
            found = True
            try:
                arr = json.loads(ln.split(":", 1)[1])
            except ValueError:
                arr = []
            # Bỏ mọi biến thể Aero rồi thêm lại ở CUỐI = ưu tiên cao nhất, để
            # không pack nào của modpack đè lên nút/nền kính của mình.
            arr = [e for e in arr if e not in (PACK_NAME, "file/" + PACK_NAME)]
            arr.append(entry)
            out.append("resourcePacks:" + json.dumps(arr))
        else:
            out.append(ln)
    if not found:
        out.append("resourcePacks:" + json.dumps([entry]))
    options.parent.mkdir(parents=True, exist_ok=True)
    options.write_text("\n".join(out) + "\n")


def apply_to_instance(game_dir: Path, client_jar: Path | None = None) -> str:
    """Cài Aero UI vào instance tại game_dir. Trả về 'modern' hoặc 'legacy'.

    client_jar: jar client của bản đó (để ghép widgets.png cho bản legacy). Bỏ
    trống hoặc bản modern -> chỉ dùng sprite ship sẵn.
    """
    legacy = _legacy_widgets_png(client_jar) if client_jar else None
    modern = legacy is None
    _build_zip(Path(game_dir) / "resourcepacks" / PACK_NAME, legacy)
    _enable_in_options(Path(game_dir) / "options.txt", modern)
    return "modern" if modern else "legacy"


def remove_from_instance(game_dir: Path) -> None:
    """Gỡ Aero UI: xoá zip và bỏ khỏi options.txt (tắt công tắc)."""
    gd = Path(game_dir)
    (gd / "resourcepacks" / PACK_NAME).unlink(missing_ok=True)
    options = gd / "options.txt"
    if not options.exists():
        return
    out = []
    for ln in options.read_text().splitlines():
        if ln.startswith("resourcePacks:"):
            try:
                arr = [e for e in json.loads(ln.split(":", 1)[1])
                       if e not in (PACK_NAME, "file/" + PACK_NAME)]
            except ValueError:
                arr = []
            out.append("resourcePacks:" + json.dumps(arr))
        else:
            out.append(ln)
    options.write_text("\n".join(out) + "\n")
