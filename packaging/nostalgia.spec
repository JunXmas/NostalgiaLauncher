# -*- mode: python ; coding: utf-8 -*-
"""Spec dùng chung cho cả ba nền tảng.

Chỉ có một file spec chứ không phải mỗi hệ điều hành một bản: phần lớn cấu hình
là như nhau, tách ra thì ba file lệch nhau dần mà không ai để ý. Chỗ nào thật sự
khác biệt thì rẽ nhánh ngay tại đó, kèm lý do.

Chạy từ thư mục gốc của dự án:
    pyinstaller packaging/nostalgia.spec --noconfirm
"""

import sys
from pathlib import Path

# SPECPATH do PyInstaller đặt sẵn: đường dẫn tới thư mục chứa file spec này.
ROOT = Path(SPECPATH).parent
ASSETS = ROOT / "packaging" / "assets"

APP_NAME = "Nostalgia Launcher"
APP_VERSION = "0.2.4"
BUNDLE_ID = "com.nostalgia.launcher"

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"

# Trên Windows/macOS tên file thực thi chính là thứ người dùng nhìn thấy, nên để
# nguyên dấu cách cho đẹp. Trên Linux nó nằm trong PATH và bị gõ tay, nên dùng
# slug — không ai muốn phải escape dấu cách trong terminal.
EXE_NAME = APP_NAME if (WINDOWS or MACOS) else "nostalgia-launcher"

icon = None
if WINDOWS and (ASSETS / "icon.ico").exists():
    icon = str(ASSETS / "icon.ico")
elif MACOS and (ASSETS / "icon.icns").exists():
    icon = str(ASSETS / "icon.icns")

a = Analysis(
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "nostalgia" / "ui" / "assets"), "nostalgia/ui/assets")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # Bỏ những thứ chắc chắn không đụng tới. Không phải để tiết kiệm dung lượng
    # cho vui: PySide6 kéo theo WebEngine thì gói phồng thêm hàng trăm MB, và
    # tkinter trên macOS còn lôi cả Tcl/Tk của hệ thống vào rồi hỏng chữ ký.
    excludes=[
        "tkinter", "unittest", "pydoc_data", "test",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
        "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtMultimedia", "PySide6.QtBluetooth",
        "PySide6.QtPositioning", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtOpenGL",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX hay bị diệt virus báo nhầm — không đáng đổi
    # console=False là điều kiện sống còn trên Windows: để True thì mỗi lần mở
    # launcher lại kèm một cửa sổ dòng lệnh đen, và người dùng đóng nhầm nó là
    # cả app tắt theo.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,   # None = build theo kiến trúc của máy đang chạy
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=EXE_NAME,
)

if MACOS:
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier=BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            # Thiếu cờ này thì macOS phóng to app bằng cách nội suy điểm ảnh và
            # toàn bộ giao diện trông nhoè trên màn Retina.
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "LSApplicationCategoryType": "public.app-category.games",
            "NSRequiresAquaSystemAppearance": False,
        },
    )
