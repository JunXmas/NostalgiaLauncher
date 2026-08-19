#!/usr/bin/env bash
# Đóng bản PyInstaller (dist/nostalgia-launcher/) thành gói .deb cài được trên
# Linux Mint / Ubuntu / Debian: double-click là Software Manager cài, có sẵn
# shortcut trong menu và icon.
#
#   bash packaging/linux/build-deb.sh
#
# Kết quả: dist/installer/NostalgiaLauncher-<phiên bản>-amd64.deb
set -euo pipefail

APP_NAME="Nostalgia Launcher"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Một nguồn phiên bản duy nhất: đọc từ nostalgia/__init__.py.
VERSION="$(grep -oP '__version__ = "\K[^"]+' "$ROOT/nostalgia/__init__.py")"
BUILD="$ROOT/dist/nostalgia-launcher"          # thư mục PyInstaller one-dir
ICON="$ROOT/packaging/assets/icon.png"
OUT_DIR="$ROOT/dist/installer"
ARCH="amd64"

[ -d "$BUILD" ] || { echo "Không thấy $BUILD — chạy pyinstaller trước." >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
chmod 0755 "$STAGE"   # mktemp tạo 700; gói .deb cần thư mục gốc 755

# --- bố trí cây thư mục theo chuẩn FHS ---
install -d "$STAGE/opt/NostalgiaLauncher"
cp -r "$BUILD/." "$STAGE/opt/NostalgiaLauncher/"

install -d "$STAGE/usr/bin"
ln -s /opt/NostalgiaLauncher/nostalgia-launcher "$STAGE/usr/bin/nostalgia-launcher"

install -d "$STAGE/usr/share/applications"
cat > "$STAGE/usr/share/applications/nostalgia-launcher.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
GenericName=Minecraft Launcher
Comment=A Minecraft launcher with a frosted Windows 7 Aero look
Exec=/opt/NostalgiaLauncher/nostalgia-launcher
Icon=nostalgia-launcher
Terminal=false
Categories=Game;
StartupWMClass=nostalgia-launcher
EOF

if [ -f "$ICON" ]; then
    install -d "$STAGE/usr/share/icons/hicolor/256x256/apps"
    cp "$ICON" "$STAGE/usr/share/icons/hicolor/256x256/apps/nostalgia-launcher.png"
fi

# --- metadata gói ---
INSTALLED_KB="$(du -sk "$STAGE" | cut -f1)"
install -d "$STAGE/DEBIAN"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: nostalgia-launcher
Version: $VERSION
Section: games
Priority: optional
Architecture: $ARCH
Installed-Size: $INSTALLED_KB
Depends: libxcb-cursor0
Maintainer: JunXmas <noreply@users.noreply.github.com>
Description: Nostalgia Launcher
 A Minecraft launcher with a frosted Windows 7 Aero look — Vanilla and Fabric,
 automatic Java, a Modrinth mod library, and Microsoft sign-in.
EOF

mkdir -p "$OUT_DIR"
DEB="$OUT_DIR/NostalgiaLauncher-$VERSION-$ARCH.deb"
rm -f "$DEB"
# root:root, quyền chuẩn — dpkg-deb tôn trọng chủ sở hữu hiện tại, mà trên CI
# thư mục tạm thuộc user runner; --root-owner-group ép về root cho gọn.
dpkg-deb --root-owner-group --build "$STAGE" "$DEB"

echo "==> Xong: $DEB"
