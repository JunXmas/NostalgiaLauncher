#!/usr/bin/env bash
# Đóng "Nostalgia Launcher.app" thành một file .dmg cài được.
#
# Chạy trên macOS, sau khi PyInstaller đã tạo xong dist/Nostalgia Launcher.app:
#   bash packaging/macos/build-dmg.sh
#
# Kết quả: dist/installer/NostalgiaLauncher-<phiên bản>-<kiến trúc>.dmg
set -euo pipefail

APP_NAME="Nostalgia Launcher"
VERSION="0.3.0"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$ROOT/dist/$APP_NAME.app"
OUT_DIR="$ROOT/dist/installer"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

[ -d "$APP" ] || { echo "Không thấy $APP — chạy pyinstaller trước." >&2; exit 1; }

ARCH="$(uname -m)"
DMG="$OUT_DIR/NostalgiaLauncher-$VERSION-$ARCH.dmg"
mkdir -p "$OUT_DIR"
rm -f "$DMG"

# Ký ad-hoc. Trên Apple Silicon đây không phải bước làm cho đẹp mà là bắt buộc:
# macOS từ chối nạp mã arm64 hoàn toàn không có chữ ký, app sẽ bị giết ngay khi
# mở. Chữ ký ad-hoc (`-s -`) không cần tài khoản Developer nào và đủ để qua cửa
# đó — Gatekeeper vẫn cảnh báo "nhà phát triển chưa xác định", xem README.
echo "==> Ký ad-hoc"
codesign --force --deep --sign - "$APP"
codesign --verify --verbose=1 "$APP" || true

# Bố trí đúng thứ người dùng mong đợi khi mở .dmg: app ở bên trái, lối tắt tới
# Applications ở bên phải, kéo từ trái sang phải là xong.
echo "==> Dựng nội dung ảnh đĩa"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

echo "==> Tạo $DMG"
# hdiutil hay báo "Resource busy" chập chờn trên runner CI (Spotlight index thư
# mục tạm, hoặc ảnh đĩa trước chưa nhả xong). Thử lại vài lần thay vì rớt cả bản.
for attempt in 1 2 3 4; do
    if hdiutil create \
        -volname "$APP_NAME" \
        -srcfolder "$STAGE" \
        -ov -format UDZO \
        "$DMG"; then
        break
    fi
    if [ "$attempt" -eq 4 ]; then
        echo "hdiutil create thất bại sau 4 lần thử." >&2
        exit 1
    fi
    echo "hdiutil bận, thử lại lần $((attempt + 1)) sau 5s…" >&2
    sleep 5
done

echo "==> Xong: $DMG"
