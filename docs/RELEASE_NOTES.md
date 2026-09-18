## Nostalgia Launcher 1.0.13

Bản vá Windows, đồng thời giữ toàn bộ phần dọn dẹp và sửa lỗi nhập modpack từ 1.0.12.

### Chơi trên Windows

- **Minecraft không còn mở kèm cửa sổ CMD.** Java giờ chạy với `CREATE_NO_WINDOW`, nên đóng
  nhầm cửa sổ console không còn làm Minecraft tắt theo.

### Dọn dẹp nhập modpack

- Gỡ nút nhập từ file và wrapper trùng lặp; thống nhất tên tham số `display_label`.
- Vẫn giữ tên thật đọc từ pack khi ô tên để trống, và vẫn hiện lỗi khi chọn nhầm file.

Tải xuống và ghi chú từng nền tảng: xem bảng ở mục 1.0 phía dưới. Nhớ đối chiếu
`SHA256SUMS` với file tải về.

---

## Nostalgia Launcher 1.0.12

Bản vá khẩn cấp (hotfix). Gộp cả phần sửa của 1.0.11 — bản đó dựng xong nhưng chưa từng
phát hành, nên ai đang chạy 1.0.10 sẽ nhận thẳng bản này.

### Nhập bản chơi / modpack từ file

- **Bản chơi không còn mang tên file thay vì tên pack.** Nhập một modpack mà không gõ gì vào
  ô tên thì launcher lấy tên thật đọc trong `modrinth.index.json`. Trước đây tải "Gói Vui" về
  máy thành `tai-ve.mrpack` thì thẻ bản chơi hiện `tai-ve`.
- **Chọn nhầm file không còn im lặng.** Lỗi khi nhập từ file giờ hiện trên dải báo lỗi; trước
  đây cú bấm đó không có chuyện gì xảy ra.
- **Gỡ nút "Nhập modpack từ file" trùng lặp** ở trang Bản chơi — hộp thoại *Nhập bản chơi* đã
  có sẵn tab làm đúng việc đó.

### Tự cập nhật trên Linux

- **Sửa lỗi `Exception occurred in preexec_fn`** khi launcher chạy script tráo bản mới. Lỗi
  xảy ra khi launcher đã là session leader (mở từ terminal, từ file `.desktop`, hoặc systemd):
  `os.setsid()` ném *Operation not permitted* và bản cập nhật không áp được. Đã thay bằng
  `start_new_session=True`, an toàn trong mọi trường hợp.

### Cài đặt

- **"Chọn ổ khác" không còn im lặng** khi đường dẫn không hợp lệ (đã có trong 1.0.10).

Tải xuống và ghi chú từng nền tảng: xem bảng ở mục 1.0 phía dưới. Nhớ đối chiếu
`SHA256SUMS` với file tải về.

---

## Nostalgia Launcher 1.0.6

Bản vá khẩn cấp (hotfix) gồm hai sửa lỗi:

- **Sửa lỗi cài đặt .deb trên Linux Mint** (MYLA-19) — file `.deb` trước đây dùng nén zstd
  mà các phiên bản `dpkg`/`apt` trên Linux Mint (và Ubuntu cũ) chưa hỗ trợ, khiến cài đặt
  thất bại. Đã chuyển sang nén xz để tương thích rộng hơn.
- **Sửa lỗi giao diện responsive trên màn hình nhỏ** (MYLA-20) — trên màn hình 1366×768,
  các nút bấm bị chèn lên nhau hoặc biến mất. Đã giảm kích thước tối thiểu cửa sổ, bổ sung
  ScrollView, và sử dụng responsive layout để đảm bảo hiển thị tốt từ 1024×768 trở lên.

---

## Nostalgia Launcher 1.0.5

Bản vá khẩn cấp (hotfix) sửa lỗi tính năng tự động cập nhật (auto-update) tải xong nhưng không áp dụng cài đặt trên mọi nền tảng (Windows, macOS, Linux).

---

## Nostalgia Launcher 1.0.4

Bản sửa lỗi cho hai vấn đề liên quan đến `freetype.dll`:

- **Sửa crash khi chạy game** — một số phiên bản Minecraft có hai thư viện LWJGL cùng đóng
  `freetype.dll` nhưng kích thước khác nhau. Trước đây launcher báo lỗi đỏ
  *"hai thư viện natives cùng đòi tên 'freetype.dll' với nội dung khác nhau"* và không chạy
  game được. Giờ launcher giữ bản lớn hơn (đầy đủ hơn) và game chạy bình thường.
- **Sửa lỗi build Windows** (từ v1.0.3) — PyInstaller + PySide6 trên Windows đóng gói hai bản
  `freetype.dll` khác nhau khiến gói không chạy. Đã loại bản thừa.

Linux and Windows builds of 1.0.2 will offer this update automatically. Downloads and platform
notes are the same as 1.0 below.

---

## Nostalgia Launcher 1.0.1

A small polish release on top of 1.0:

- **Sharper home screen.** The hero image now ships at its full 2528 px, adaptively sharpened,
  and is drawn with mipmaps — about twice the edge detail at display size.
- **Continue playing** (already in the final 1.0 build): your most recent worlds across all
  instances as Minecraft-style block buttons; one click launches the instance straight into that
  world (quick play, Minecraft 1.20+).
- CI flake in the modpack-import test fixed.

Downloads and platform notes are the same as 1.0 below. If you run 1.0.0 on Linux or Windows,
the launcher will offer this update by itself.

---

## Nostalgia Launcher 1.0 — the rework

The first release of the from-scratch rewrite of Nostalgia Launcher. Same name, same heart,
none of the old code: 130 commits, 770 tests, one façade between the UI and the engine, and a
rule that nothing ships without a test.

### What's new compared to the old NostalgiaLauncher

- **Accounts**: Microsoft, **Ely.by** (authlib-injector verified by SHA-256) and offline, side by side.
- **Instances**: Vanilla, Fabric, **Quilt**, Forge, NeoForge and an **Optimized** preset; each
  instance can live in **its own folder on any disk**; per-instance play time, launches, worlds, mods.
- **Create dialog**: official key art per Minecraft generation, cards that light up and lift,
  versions sliding down as stone buttons.
- **Library**: Modrinth **and CurseForge** (no API key), modpack import by file or **drag & drop**.
- **Play together**: LAN over relay with 18-character room codes and ten tested security rules.
- **Skins**: a skin library inside the launcher; one *Thêm skin* button that uploads to Mojang
  for Microsoft accounts and applies instantly for everyone else.
- **Feedback**: live game log with filters, toasts + chimes, soft dashboard-style UI sounds,
  Discord Rich Presence (off by default).
- **Auto-update** with mandatory `SHA256SUMS` verification (Linux and Windows packages apply
  themselves; macOS shows the download page).
- **Engineering**: zero runtime dependencies in the core, 7-layer architecture with tests
  guarding the boundaries, every file ≤ 200 lines, ruff + mypy strict, CI on Python 3.12 / 3.13.

### Downloads

| Platform | File | Notes |
|---|---|---|
| Linux (any distro) | `nostalgia-<ver>-linux-x64.AppImage` | `chmod +x`, double-click. Needs glibc ≥ 2.35 (Ubuntu 22.04+, Debian 12+, Mint 21+, Fedora 36+, Arch). |
| Debian / Ubuntu / Mint / Pop!_OS | `nostalgia_<ver>_amd64.deb` | `sudo apt install ./nostalgia_<ver>_amd64.deb` |
| Fedora / openSUSE / RHEL / Nobara | `nostalgia-<ver>-1.x86_64.rpm` | `sudo dnf install ./nostalgia-<ver>-1.x86_64.rpm` |
| Linux, portable | `nostalgia-<ver>-linux-x64.tar.gz` / `.zip` | unpack, run `Nostalgia/nostalgia-ui` |
| macOS Apple Silicon | `nostalgia-<ver>-macos-arm64.dmg` | drag to Applications; first launch: right-click → Open (unsigned) |
| macOS Intel | `nostalgia-<ver>-macos-x64.dmg` | same |
| Windows 10/11 x64 | `nostalgia-<ver>-windows-x64-setup.exe` | installer, no admin needed; SmartScreen → "More info → Run anyway" (unsigned) |
| Windows, portable | `nostalgia-<ver>-windows-x64.zip` | unpack, run `Nostalgia\nostalgia-ui.exe` |

Verify any download against `SHA256SUMS`. The zips are what the built-in updater downloads.

### Not back yet

Pixel skin editor, translations (the UI is Vietnamese for now). They are coming, on top of a
codebase that can carry them.
