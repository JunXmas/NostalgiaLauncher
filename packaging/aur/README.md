# packaging/aur

Gói `nostalgia-bin` cho AUR: lấy `nostalgia-<ver>-linux-x64.tar.gz` dựng sẵn từ
[GitHub Releases](https://github.com/JunXmas/NostalgiaLauncher/releases), không build lại
từ nguồn.

## Đã kiểm

- `sha256sums` trong `PKGBUILD` khớp `SHA256SUMS` của release `v1.0.15` (tar.gz, desktop
  file, icon 256px, LICENSE — cả bốn tính tay bằng `sha256sum` trên nội dung tải thật, đối
  chiếu với `git show v1.0.15:<path> | sha256sum` cho ba file lấy từ repo).
- `PKGBUILD` và `.SRCINFO` khớp nhau từng trường (`pkgver`, `pkgrel`, `depends`, `source`,
  `sha256sums`) — so bằng script Python, không phải bằng mắt.
- `depends` ánh xạ 1:1 từ `packaging/linux/debian-control` (đã dùng để build .deb chạy
  thật trong CI) sang tên gói kho `extra` của Arch, tra từng gói trên archlinux.org:

  | debian-control (.deb) | Arch (extra) | Ghi chú |
  |---|---|---|
  | `libxcb-cursor0` | `xcb-util-cursor` | |
  | `libxkbcommon0` | `libxkbcommon` | |
  | `libegl1`, `libgl1` | `libglvnd` | Arch gộp EGL/GL vào một gói dispatch |
  | `libfontconfig1` | `fontconfig` | |
  | `libdbus-1-3` | `dbus` | |
  | `libglib2.0-0` | `glib2` | |
  | `libxcb-icccm4` | `xcb-util-wm` | gói này chứa cả icccm lẫn ewmh |
  | `libxcb-image0` | `xcb-util-image` | |
  | `libxcb-keysyms1` | `xcb-util-keysyms` | |
  | `libxcb-render-util0` | `xcb-util-renderutil` | |
  | `libxcb-shape0`, `libxcb-xinerama0` | (đã có trong `libxcb`) | Arch không tách hai ext này thành gói riêng |

  Đối chiếu thêm với danh sách `.so` thật bên trong `nostalgia-1.0.15-linux-x64.tar.gz`
  (`Nostalgia/_internal/*.so*`) để không thiếu thư viện nào launcher thật sự nạp.

## Chưa kiểm — cần máy Arch thật

Máy chạy agent này (Linux Mint 22.3) không có `makepkg`/`base-devel`/`pacman`, nên
**chưa chạy được** `makepkg -si`, `namcap`, hay `makepkg --printsrcinfo` để tự sinh
`.SRCINFO`. `.SRCINFO` ở đây viết tay và kiểm khớp `PKGBUILD` bằng script so trường, nhưng
chưa được `makepkg` xác nhận là đúng cú pháp AUR đòi. Trước khi đẩy lên AUR, nên chạy trên
máy Arch (hoặc container `archlinux:base-devel`):

```sh
cd packaging/aur
makepkg --printsrcinfo > .SRCINFO   # sinh lại, so với bản viết tay
makepkg -si                          # build + cài thật, xem app chạy được không
namcap PKGBUILD nostalgia-bin-1.0.15-1-x86_64.pkg.tar.zst
```

## Không tự đẩy lên AUR

Đẩy `nostalgia-bin` lên `aur.archlinux.org` là publish — chủ dự án quyết định lúc nào.

## Việc tiếp theo (ngoài phạm vi issue này)

Flatpak: launcher đối thủ đã lên Flathub. Việc lớn hơn nhiều — cần viết manifest riêng,
gửi lên Flathub, chờ họ soát — không làm trong issue AUR này.
