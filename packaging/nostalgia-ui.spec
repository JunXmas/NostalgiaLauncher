# -*- mode: python ; coding: utf-8 -*-
"""Gói `nostalgia-ui` dạng onedir cho PyInstaller.

    uv run --group build pyinstaller packaging/nostalgia-ui.spec

Onedir (một thư mục) thay vì onefile: bộ tự cập nhật tráo CẢ THƯ MỤC sau khi launcher thoát,
và khởi động nhanh hơn vì không phải bung 100 MB vào thư mục tạm mỗi lần mở.
"""

import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent
PACKAGE = ROOT / "src" / "nostalgia"
VERSION = re.search(r'__version__ = "([^"]+)"', (PACKAGE / "__init__.py").read_text(encoding="utf-8")).group(1)
ICONS = ROOT / "packaging" / "icons"
# Icon theo hệ: Windows nhúng .ico vào exe; macOS dùng .icns do workflow sinh từ PNG bằng
# iconutil (chỉ có trên macOS); Linux lấy PNG qua .desktop nên không cần ở đây.
EXE_ICON = str(ICONS / "nostalgia.ico") if sys.platform == "win32" else None
APP_ICON = str(ICONS / "nostalgia.icns") if (ICONS / "nostalgia.icns").is_file() else None

# QML, ảnh, skin mặc định: PyInstaller không tự thấy file được nạp bằng đường dẫn lúc chạy.
datas = [
    (str(PACKAGE / "ui" / "qml"), "nostalgia/ui/qml"),
    (str(PACKAGE / "skin" / "defaults"), "nostalgia/skin/defaults"),
]
datas += collect_data_files("PySide6", subdir="Qt/qml", includes=["QtQuick/**", "QtQml/**", "QtQuick.2/**"])

block_cipher = None

# Sửa lỗi PyInstaller Windows: hai thư viện đều đóng gói freetype.dll khác nhau
def filter_binaries(binaries):
    seen = set()
    result = []
    for dst, src, typ in binaries:
        name = Path(dst).name
        if name == "freetype.dll" and name in seen:
            continue
        seen.add(name)
        result.append((dst, src, typ))
    return result

analysis = Analysis(
    [str(ROOT / "packaging" / "entry_ui.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtQuickControls2"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore"],
    noarchive=False,
)

# Loại bỏ bản trùng lặp của freetype.dll trên Windows
if sys.platform == "win32":
    analysis.binaries = filter_binaries(analysis.binaries)
pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="nostalgia-ui",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=EXE_ICON,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipped_data,
    analysis.datas,
    strip=False,
    upx=False,
    name="nostalgia-ui",
)
# macOS: bọc thêm thành .app để kéo vào Applications và đóng .dmg; thư mục onedir vẫn được
# giữ trong dist/nostalgia-ui cho gói zip của bộ tự cập nhật.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Nostalgia Launcher.app",
        icon=APP_ICON,
        bundle_identifier="dev.junxmas.nostalgia",
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
        },
    )
