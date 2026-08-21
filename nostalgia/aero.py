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
import re
import shutil
import zipfile
from pathlib import Path

from .paths import CONFIG_DIR

PACK_NAME = "Aero UI.zip"
PACK_DIR = Path(__file__).resolve().parent / "ui" / "assets" / "aero-pack"
# Layout FancyMenu Aero (viết tay) + ảnh nền, ship kèm launcher. Chỉ có tác dụng
# khi instance đã cài mod FancyMenu (xem app._install_aero_mods_async).
FANCYMENU_DIR = Path(__file__).resolve().parent / "ui" / "assets" / "fancymenu"
# Panorama title screen theo chế độ sáng/tối: day/ (ban ngày) và night/ (ban đêm),
# mỗi bộ 6 mặt panorama_0..5. Ghi đè panorama trong pack lúc đóng gói.
PANORAMA_DIR = Path(__file__).resolve().parent / "ui" / "assets" / "panoramas"
PANO_REL = "assets/minecraft/textures/gui/title/background"
# Theme panorama do người dùng thêm (mỗi theme = 1 thư mục panorama_0..5.png).
USER_PANORAMA_DIR = CONFIG_DIR / "panoramas"
# Theme dựng sẵn: ánh xạ id -> tên hiển thị (2 bộ day/night đã ship kèm launcher).
_BUILTIN_PANORAMAS = (("day", "Aero Day"), ("night", "Aero Night"))


def _slug(name: str) -> str:
    """Tên theme -> slug an toàn làm tên thư mục."""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "theme"


def _theme_faces(pano_dir: Path) -> bool:
    """Thư mục có đủ mặt panorama_0 để coi là một theme dùng được."""
    return pano_dir.is_dir() and (pano_dir / "panorama_0.png").exists()


def panorama_themes() -> list[dict]:
    """Danh sách theme panorama chọn được: 2 bộ dựng sẵn (day/night) + các theme
    người dùng nhập ở USER_PANORAMA_DIR. Mỗi mục: id, name, dir, preview, builtin."""
    out: list[dict] = []
    for tid, name in _BUILTIN_PANORAMAS:
        d = PANORAMA_DIR / tid
        if _theme_faces(d):
            out.append({"id": tid, "name": name, "dir": d,
                        "preview": d / "panorama_0.png", "builtin": True})
    if USER_PANORAMA_DIR.is_dir():
        for d in sorted(USER_PANORAMA_DIR.iterdir()):
            if _theme_faces(d):
                out.append({"id": d.name, "name": d.name.replace("-", " ").title(),
                            "dir": d, "preview": d / "panorama_0.png", "builtin": False})
    return out


def _panorama_dir(panorama_theme: str, dark: bool) -> Path:
    """Thư mục 6 mặt panorama sẽ dùng: theo theme đã chọn nếu hợp lệ, ngược lại
    quay về day/night theo cờ dark (giữ tương thích ngược khi chưa chọn theme)."""
    if panorama_theme:
        for t in panorama_themes():
            if t["id"] == panorama_theme and _theme_faces(t["dir"]):
                return t["dir"]
    return PANORAMA_DIR / ("night" if dark else "day")


def import_panorama_theme(name: str, faces: list[Path]) -> str:
    """Nhập một theme panorama từ 6 file panorama_0..5 (thứ tự theo faces). Chép
    vào USER_PANORAMA_DIR/<slug>. Trả về id (slug) của theme."""
    slug = _slug(name)
    dest = USER_PANORAMA_DIR / slug
    dest.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(faces[:6]):
        shutil.copyfile(f, dest / f"panorama_{i}.png")
    return slug


def _inject_panorama_into_jar(jar_path: Path, pano_dir: Path) -> None:
    """Thay 6 mặt panorama (và BỎ panorama_overlay tĩnh) trong pack nhúng của mod
    hard-lock, để theme panorama đã chọn có tác dụng cả trên instance hard-lock."""
    if not _theme_faces(pano_dir):
        return
    rel = f"resourcepacks/aero-ui/{PANO_REL}"
    drop = {f"{rel}/panorama_{i}.png" for i in range(6)}
    drop.add(f"{rel}/panorama_overlay.png")
    with zipfile.ZipFile(jar_path) as zin:
        keep = [(it, zin.read(it.filename)) for it in zin.infolist()
                if it.filename not in drop]
    tmp = jar_path.with_suffix(".jar.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it, data in keep:
            zout.writestr(it, data)
        for i in range(6):
            zout.write(pano_dir / f"panorama_{i}.png", f"{rel}/panorama_{i}.png")
    tmp.replace(jar_path)
MOD_NAME = "aero-ui-mod.jar"
_ASSETS = Path(__file__).resolve().parent / "ui" / "assets"
# Jar hard-lock Fabric build từ MỘT source, mỗi era một bản (xem aero-ui-mod/):
#   • 121: 1.21.x obfuscate -> intermediary. Verify chạy 1.21.11 (pack_format 75).
#   • 26x: 26.x KHÔNG obfuscate -> tên Mojang. Verify chạy 26.2 (pack_format 88).
# Mixin để `required` nên CHỈ áp cho bản đã verify (khớp format), kẻo sai target thì
# crash lúc load — bản không khớp rơi về soft-lock (an toàn).
MOD_JAR_FABRIC_121 = _ASSETS / "aero-ui-mod-121.jar"
MOD_JAR_FABRIC_26X = _ASSETS / "aero-ui-mod-26x.jar"


def _obfuscated(mc: str) -> bool:
    """Bản CÒN obfuscate (chạy runtime intermediary) hay không. Ranh giới của
    Fabric: ≤1.21.11 obfuscate; 26.1+ (đánh số mới, không bắt đầu bằng "1.") thì
    không. Dùng để tách jar intermediary khỏi jar Mojang-native."""
    return mc.startswith("1.")


# Registry artifact hard-lock: (loader, đường-dẫn-jar, vị-ngữ-khớp). Auto-chọn theo
# (loader, mc, pack_format) của TỪNG instance. Thêm era mới = thêm một dòng ở đây.
# Hiện chỉ có 1.21.x Fabric; 26.x / Fabric cũ / Forge sẽ bổ sung sau (rơi soft-lock).
_HARD_LOCK_ARTIFACTS = [
    ("fabric", MOD_JAR_FABRIC_121,
     lambda mc, fmt: _obfuscated(mc) and fmt == 75),        # 1.21.11
    ("fabric", MOD_JAR_FABRIC_26X,
     lambda mc, fmt: not _obfuscated(mc) and fmt == 88),    # 26.2
]


def select_hard_lock(loader: str, mc: str, pack_format: int) -> Path | None:
    """Chọn jar/coremod hard-lock hợp instance, hoặc None (→ soft-lock)."""
    for a_loader, jar, matches in _HARD_LOCK_ARTIFACTS:
        if loader == a_loader and jar.exists() and matches(mc or "", pack_format):
            return jar
    return None

SPRITES = "assets/minecraft/textures/gui/sprites/widget"
WIDGETS = "assets/minecraft/textures/gui/widgets.png"
# Toạ độ 3 trạng thái nút trong widgets.png (256×256), mỗi vùng 200×20.
BTN_REGIONS = {"button_disabled.png": 46, "button.png": 66, "button_highlighted.png": 86}

PACK_DESC = "§bAero glass UI §7— Nostalgia Launcher"
# Bản không có version.json (≤ 1.12.2) -> pack_format 3: 1.12.2 nhận sạch, còn
# 1.8–1.11 chỉ hiện cảnh báo "incompatible" nhưng vẫn nạp pack (bản cũ không
# chặn cứng). 1.13+ luôn có version.json nên lấy đúng số.
_LEGACY_PACK_FORMAT = 3


def _pack_format(client_jar: Path | None) -> int:
    """Số resource pack_format ĐÚNG cho chính bản này, đọc từ `version.json` trong
    jar (`pack_version.resource_major`). Nhờ vậy launcher tự khớp mọi era —
    1.16.5(6) … 1.21.11(75) … 26.x(cao hơn) — không đoán theo tên phiên bản.
    """
    if client_jar:
        try:
            with zipfile.ZipFile(client_jar) as z:
                if "version.json" in z.namelist():
                    pv = json.loads(z.read("version.json")).get("pack_version")
                    if isinstance(pv, dict):
                        val = pv.get("resource_major", pv.get("resource"))
                        if isinstance(val, int):
                            return val
                    elif isinstance(pv, int):
                        return pv
        except (OSError, zipfile.BadZipFile, ValueError):
            pass
    return _LEGACY_PACK_FORMAT


def _mcmeta(pack_format: int) -> bytes:
    """pack.mcmeta khai báo CẢ hai lược đồ để nạp sạch trên mọi era:
      • `pack_format` — bản cũ (≤ 1.21.8) đọc field này.
      • `min_format`/`max_format` — từ snapshot 25w31a (1.21.9+, gồm 26.x) BẮT BUỘC,
        thiếu là bản mới GỠ pack ("missing mandatory fields min_format and max_format").
    Bản không hiểu field lạ thì bỏ qua, nên một file phủ hết.
    """
    meta = {"pack": {
        "pack_format": pack_format,
        "min_format": pack_format,
        "max_format": pack_format,
        "description": PACK_DESC,
    }}
    return json.dumps(meta, indent=2).encode("utf-8")


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


def _build_zip(dest: Path, legacy_widgets: bytes | None, dark: bool = False,
               pack_format: int = _LEGACY_PACK_FORMAT,
               panorama_theme: str = "") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Bộ panorama theo THEME đã chọn (hoặc day/night theo dark); có thì THAY 6 mặt
    # panorama trong pack và BỎ panorama_overlay (overlay tĩnh — bỏ để panorama XOAY
    # như title gốc). Không có bộ ảnh thì giữ nguyên panorama sẵn trong pack.
    pano_src = _panorama_dir(panorama_theme, dark)
    use_pano = _theme_faces(pano_src)
    # pack.mcmeta tĩnh trong PACK_DIR bị BỎ QUA; ta ghi bản tính theo phiên bản
    # (đúng pack_format của chính instance) để nạp sạch trên mọi era.
    skip = {"pack.mcmeta"}
    if use_pano:
        skip |= {f"{PANO_REL}/panorama_{i}.png" for i in range(6)}
        skip.add(f"{PANO_REL}/panorama_overlay.png")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", _mcmeta(pack_format))
        for f in sorted(PACK_DIR.rglob("*")):
            if f.is_file():
                rel = f.relative_to(PACK_DIR).as_posix()
                if rel in skip:
                    continue
                z.write(f, rel)
        if use_pano:
            for i in range(6):
                face = pano_src / f"panorama_{i}.png"
                if face.exists():
                    z.write(face, f"{PANO_REL}/panorama_{i}.png")
        if legacy_widgets is not None:
            z.writestr(WIDGETS, legacy_widgets)


def _set_option(options: Path, key: str, value: str) -> None:
    """Đặt (ghi đè) một dòng `key:value` trong options.txt, giữ các dòng khác.

    Dùng để kéo `menuBackgroundBlurriness` lên max -> vanilla blur thế giới sau
    menu mạnh nhất, cộng lớp tint kính Aero của pack = frosted acrylic. Bản cũ
    không có tuỳ chọn này thì thêm dòng thừa vô hại, game bỏ qua.
    """
    lines = options.read_text().splitlines() if options.exists() else []
    out, found = [], False
    for ln in lines:
        if ln.startswith(key + ":"):
            out.append(f"{key}:{value}"); found = True
        else:
            out.append(ln)
    if not found:
        out.append(f"{key}:{value}")
    options.parent.mkdir(parents=True, exist_ok=True)
    options.write_text("\n".join(out) + "\n")


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


def apply_to_instance(game_dir: Path, client_jar: Path | None = None,
                      *, mc: str = "", loader: str = "", dark: bool = False,
                      panorama_theme: str = "") -> str:
    """Cài Aero UI vào instance tại game_dir — launcher TỰ chọn cách khoá theo bản.

    Nếu có artifact hard-lock hợp (loader, mc, pack_format) — xem
    select_hard_lock(): cài mod/coremod ALWAYS_ENABLED vào mods/ để người chơi
    KHÔNG tắt được pack (và bỏ resource pack thường vì mod đã kèm pack). Trả 'locked'.

    Không có artifact hợp: soft-lock — cài resource pack (ghép widgets.png cho bản
    legacy từ client_jar, pack.mcmeta đúng format của bản) và bật trong options.txt.
    Trả 'modern'/'legacy'.

    panorama_theme: id theme panorama (xem panorama_themes()) — áp cho cả hard-lock
    (nhúng vào jar) lẫn soft-lock (thay trong pack). Rỗng = day/night theo dark.
    """
    gd = Path(game_dir)
    fmt = _pack_format(client_jar)
    jar = select_hard_lock(loader, mc, fmt)
    if jar is not None:
        mods = gd / "mods"
        mods.mkdir(parents=True, exist_ok=True)
        dest_jar = mods / MOD_NAME
        shutil.copyfile(jar, dest_jar)
        # Theme panorama đã chọn: nhúng thẳng vào bản jar trong instance để có tác
        # dụng dù pack của mod đang top-priority. Rỗng = giữ panorama gốc của mod.
        if panorama_theme:
            _inject_panorama_into_jar(dest_jar, _panorama_dir(panorama_theme, dark))
        (gd / "resourcepacks" / PACK_NAME).unlink(missing_ok=True)   # mod đã kèm pack
        return "locked"

    legacy = _legacy_widgets_png(client_jar) if client_jar else None
    modern = legacy is None
    _build_zip(gd / "resourcepacks" / PACK_NAME, legacy, dark=dark, pack_format=fmt,
               panorama_theme=panorama_theme)
    _enable_in_options(gd / "options.txt", modern)
    # Kéo blur nền menu lên max: cùng lớp tint kính Aero trong pack -> frosted
    # acrylic. Chỉ có tác dụng ở 1.20.5+; bản cũ bỏ qua dòng này.
    _set_option(gd / "options.txt", "menuBackgroundBlurriness", "1.0")
    return "modern" if modern else "legacy"


def apply_fancymenu(game_dir: Path, lock: bool = True) -> None:
    """Cài layout FancyMenu Aero (nền title screen) vào instance, và — nếu lock —
    ẩn thanh editor của FancyMenu để KHÔNG đổi/tắt được giao diện trong game
    (hard-lock kiểu Lunar). Ghi file trực tiếp, không mạng.

    Chỉ ăn khi instance có mod FancyMenu; bản không có mod thì file này nằm im,
    vô hại. Chạy lại mỗi lần áp Aero nên trạng thái khoá luôn được ép lại.
    """
    fm = Path(game_dir) / "config" / "fancymenu"
    if not fm.is_dir():
        return
    # Nền title screen giờ do PANORAMA của resource pack lo (ngày/đêm). Gỡ nền
    # tĩnh FancyMenu cũ (ảnh Aero xanh) nếu còn, để panorama hiện lên.
    (fm / "customization" / "aero_title.txt").unlink(missing_ok=True)
    (fm / "assets" / "aero_bg.png").unlink(missing_ok=True)
    if not lock:
        return
    # Ẩn thanh Customization/Tools/Help -> người chơi không mở được editor. Chỉ
    # sửa được khi options.txt đã tồn tại (FancyMenu tạo ở lần chạy đầu); lần áp
    # sau sẽ khoá. Chỉ đụng đúng một dòng, giữ nguyên phần còn lại của config.
    opts = fm / "options.txt"
    if opts.exists():
        import re
        t = opts.read_text()
        if "show_customization_overlay" in t:
            t = re.sub(r"B:show_customization_overlay = '[^']*';",
                       "B:show_customization_overlay = 'false';", t)
            opts.write_text(t)


def remove_from_instance(game_dir: Path) -> None:
    """Gỡ Aero UI: xoá zip, mod, và bỏ khỏi options.txt (tắt công tắc)."""
    gd = Path(game_dir)
    (gd / "resourcepacks" / PACK_NAME).unlink(missing_ok=True)
    (gd / "mods" / MOD_NAME).unlink(missing_ok=True)
    # FancyMenu: xoá layout Aero và MỞ LẠI editor (bỏ hard-lock).
    fm = gd / "config" / "fancymenu"
    (fm / "customization" / "aero_title.txt").unlink(missing_ok=True)
    opts = fm / "options.txt"
    if opts.exists():
        import re
        t = opts.read_text()
        if "show_customization_overlay" in t:
            opts.write_text(re.sub(r"B:show_customization_overlay = '[^']*';",
                                   "B:show_customization_overlay = 'true';", t))
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
