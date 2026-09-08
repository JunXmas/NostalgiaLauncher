# -*- mode: python ; coding: utf-8 -*-
"""Gói `nostalgia-ui` dạng onedir cho PyInstaller.

    uv run --group build pyinstaller packaging/nostalgia-ui.spec

Onedir (một thư mục) thay vì onefile: bộ tự cập nhật tráo CẢ THƯ MỤC sau khi launcher thoát,
và khởi động nhanh hơn vì không phải bung 100 MB vào thư mục tạm mỗi lần mở.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent
PACKAGE = ROOT / "src" / "nostalgia"

# QML, ảnh, skin mặc định: PyInstaller không tự thấy file được nạp bằng đường dẫn lúc chạy.
datas = [
    (str(PACKAGE / "ui" / "qml"), "nostalgia/ui/qml"),
    (str(PACKAGE / "skin" / "defaults"), "nostalgia/skin/defaults"),
]
datas += collect_data_files("PySide6", subdir="Qt/qml", includes=["QtQuick/**", "QtQml/**", "QtQuick.2/**"])

block_cipher = None

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
