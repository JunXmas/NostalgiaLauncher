## Nostalgia Launcher 1.0.13

Bản vá Windows, đồng thời giữ toàn bộ phần dọn dẹp và sửa lỗi nhập modpack từ 1.0.12.

### Chơi trên Windows

- **Minecraft không còn mở kèm cửa sổ CMD.** Java giờ chạy với `CREATE_NO_WINDOW`, nên đóng
  nhầm cửa sổ console không còn làm Minecraft tắt theo.

### Dọn dẹp nhập modpack

- Gỡ nút nhập từ file và wrapper trùng lặp; thống nhất tên tham số `display_label`.
- Vẫn giữ tên thật đọc từ pack khi ô tên để trống, và vẫn hiện lỗi khi chọn nhầm file.

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
