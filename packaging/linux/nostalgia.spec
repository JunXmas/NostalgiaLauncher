# Spec RPM đóng gói cây PyInstaller dựng sẵn (biến _tree do build-packages.sh truyền vào).
# Tắt strip / debuginfo / build-id: binary của PyInstaller và Qt không phải để rpmbuild sửa.
%global debug_package %{nil}
%global __strip /bin/true
%global __os_install_post %{nil}
%global _build_id_links none
%define _binary_payload w2.xzdio

Name:           nostalgia
Version:        @VERSION@
Release:        1
Summary:        Nostalgia Launcher - Minecraft launcher
License:        GPL-3.0-only
URL:            https://github.com/JunXmas/NostalgiaLauncher
AutoReqProv:    no
Requires:       xcb-util-cursor, libxkbcommon, mesa-libEGL, mesa-libGL, fontconfig, dbus-libs, glib2

%description
Microsoft, Ely.by and offline accounts; Vanilla, Fabric, Quilt, Forge and
NeoForge instances; Modrinth and CurseForge library; LAN over relay; skin
library; auto-update. Installed under /opt/nostalgia.

%install
mkdir -p %{buildroot}
cp -a %{_tree}/. %{buildroot}/

%files
/opt/nostalgia
/usr/bin/nostalgia-ui
/usr/share/applications/nostalgia.desktop
/usr/share/icons/hicolor/256x256/apps/nostalgia.png
