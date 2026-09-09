#!/bin/sh
# Đóng gói Linux từ thư mục PyInstaller `dist/nostalgia-ui` thành bốn dạng cài đặt:
#   out/nostalgia-<ver>-linux-x64.tar.gz    mọi distro (bung ra chạy)
#   out/nostalgia-<ver>-linux-x64.AppImage  mọi distro, một file, không cần cài
#   out/nostalgia_<ver>_amd64.deb           Debian / Ubuntu / Mint / Pop!_OS
#   out/nostalgia-<ver>-1.x86_64.rpm        Fedora / openSUSE / RHEL / Nobara
#
#   packaging/linux/build-packages.sh 1.0.0
#
# Cần: dpkg-deb, rpmbuild (gói `rpm`), và appimagetool (biến APPIMAGETOOL, mặc định tìm trong
# PATH). Cùng một cây /opt/nostalgia + /usr/bin/nostalgia-ui + .desktop + icon dùng cho deb và
# rpm; AppImage bọc thư mục PyInstaller với AppRun mỏng.
set -eu

VERSION="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIST="$ROOT/dist/nostalgia-ui"
PKG="$ROOT/packaging/linux"
ICON="$ROOT/packaging/icons/nostalgia-256.png"
OUT="$ROOT/out"
STAGE="$ROOT/build/linux-pkg"
test -x "$DIST/nostalgia-ui" || { echo "chưa có $DIST — chạy PyInstaller trước"; exit 1; }
rm -rf "$STAGE"
mkdir -p "$OUT" "$STAGE"

# --- tar.gz: thư mục Nostalgia/ như gói zip ---------------------------------------------
tar -C "$ROOT/dist" --transform 's,^nostalgia-ui,Nostalgia,' -czf "$OUT/nostalgia-$VERSION-linux-x64.tar.gz" nostalgia-ui

# --- cây cài đặt chung cho deb và rpm --------------------------------------------------------
TREE="$STAGE/tree"
install -d "$TREE/opt/nostalgia" "$TREE/usr/bin" "$TREE/usr/share/applications" \
           "$TREE/usr/share/icons/hicolor/256x256/apps"
cp -a "$DIST/." "$TREE/opt/nostalgia/"
ln -s /opt/nostalgia/nostalgia-ui "$TREE/usr/bin/nostalgia-ui"
install -m644 "$PKG/nostalgia.desktop" "$TREE/usr/share/applications/nostalgia.desktop"
install -m644 "$ICON" "$TREE/usr/share/icons/hicolor/256x256/apps/nostalgia.png"

# --- deb ------------------------------------------------------------------------------------
DEB="$STAGE/deb"
mkdir -p "$DEB/DEBIAN"
cp -a "$TREE/." "$DEB/"
sed "s/@VERSION@/$VERSION/" "$PKG/debian-control" > "$DEB/DEBIAN/control"
dpkg-deb --build --root-owner-group "$DEB" "$OUT/nostalgia_${VERSION}_amd64.deb"

# --- rpm (máy dev Debian thường không có rpmbuild: bỏ qua, CI thì bắt buộc) -------------------
if command -v rpmbuild >/dev/null 2>&1; then
    RPMTOP="$STAGE/rpm"
    mkdir -p "$RPMTOP/BUILD" "$RPMTOP/RPMS" "$RPMTOP/SOURCES" "$RPMTOP/SPECS" "$RPMTOP/SRPMS" "$RPMTOP/BUILDROOT"
    sed "s/@VERSION@/$VERSION/" "$PKG/nostalgia.spec" > "$RPMTOP/SPECS/nostalgia.spec"
    rpmbuild -bb --quiet --define "_topdir $RPMTOP" --define "_tree $TREE" \
        --buildroot "$RPMTOP/BUILDROOT/nostalgia" "$RPMTOP/SPECS/nostalgia.spec"
    cp "$RPMTOP"/RPMS/x86_64/nostalgia-*.rpm "$OUT/"
elif [ "${CI:-}" = "true" ]; then
    echo "CI mà không có rpmbuild — cài gói rpm trước"; exit 1
else
    echo "không có rpmbuild, bỏ qua .rpm (CI vẫn dựng)"
fi

# --- AppImage -------------------------------------------------------------------------------
APPDIR="$STAGE/AppDir"
mkdir -p "$APPDIR/usr"
cp -a "$DIST" "$APPDIR/usr/nostalgia"
install -m755 "$PKG/AppRun" "$APPDIR/AppRun"
install -m644 "$PKG/nostalgia.desktop" "$APPDIR/nostalgia.desktop"
install -m644 "$ICON" "$APPDIR/nostalgia.png"
ARCH=x86_64 "${APPIMAGETOOL:-appimagetool}" --no-appstream "$APPDIR" "$OUT/nostalgia-$VERSION-linux-x64.AppImage"

ls -la "$OUT"
