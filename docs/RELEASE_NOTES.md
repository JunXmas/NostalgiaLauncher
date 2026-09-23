Cập nhật launcher giờ là **một nút**.

Trước đây launcher hiện toast bốn giây rồi bảo bạn tự vào CÀI ĐẶT → CẬP NHẬT tìm nút tải,
tải xong lại phải bấm thêm nút thứ hai để cài. Giờ có một dải xanh chạy ngang đầu cửa sổ,
thấy ở mọi trang, và bấm một lần là xong cả việc.

## Cập nhật

- **Một nút cho cả việc.** Bấm "Cập nhật ngay": launcher tải, tự cài, tự tắt và mở lại. Bạn
  không phải bấm thêm gì.
- **Dải báo bản mới ở đầu cửa sổ**, thấy ở mọi trang, cho thấy phần trăm trong lúc tải. Bấm
  ✕ để tắt; tắt rồi thì im cho tới lần mở launcher sau.
- **AppImage, `.deb` và `.rpm` cũng tự cập nhật được.** Launcher tải đúng loại gói bạn đang
  dùng: AppImage thay thẳng file đang chạy rồi mở lại; `.deb`/`.rpm` nhờ hệ điều hành cài đè
  (một hộp thoại xin mật khẩu). Gói nào cũng phải khớp `SHA256SUMS` mới được cài.
- Bản macOS `.app` và bản chạy từ mã nguồn thì mở thẳng trang tải, thay vì tải một gói rồi mới
  báo không cài được.
- Mục CẬP NHẬT ở CÀI ĐẶT vẫn còn nguyên cho ai thích chỗ cũ.

## Tải xuống

| Nền tảng | File | Ghi chú |
|---|---|---|
| Linux (mọi bản) | `nostalgia-1.0.15-linux-x64.AppImage` | `chmod +x`, bấm đúp. Cần glibc ≥ 2.35 (Ubuntu 22.04+, Debian 12+, Mint 21+, Fedora 36+, Arch). |
| Debian / Ubuntu / Mint / Pop!_OS | `nostalgia_1.0.15_amd64.deb` | `sudo apt install ./nostalgia_1.0.15_amd64.deb` |
| Fedora / openSUSE / RHEL / Nobara | `nostalgia-1.0.15-1.x86_64.rpm` | `sudo dnf install ./nostalgia-1.0.15-1.x86_64.rpm` |
| Linux, xách tay | `nostalgia-1.0.15-linux-x64.tar.gz` / `.zip` | giải nén, chạy `Nostalgia/nostalgia-ui` |
| macOS Apple Silicon | `nostalgia-1.0.15-macos-arm64.dmg` | kéo vào Applications; lần đầu: chuột phải → Open (chưa ký) |
| macOS Intel | `nostalgia-1.0.15-macos-x64.dmg` | như trên |
| Windows 10/11 x64 | `nostalgia-1.0.15-windows-x64-setup.exe` | bộ cài, không cần quyền admin; SmartScreen → "More info → Run anyway" (chưa ký) |
| Windows, xách tay | `nostalgia-1.0.15-windows-x64.zip` | giải nén, chạy `Nostalgia\nostalgia-ui.exe` |

Nhớ đối chiếu `SHA256SUMS` với file tải về — bộ tự cập nhật cũng đối chiếu đúng file này
trước khi cài, và tải về đúng loại gói bạn đang dùng.

## Cách cập nhật

Mở launcher là nó tự kiểm sau vài giây; có bản mới thì dải xanh hiện ngay trên đầu, bấm
"Cập nhật ngay" rồi để yên — launcher tự tải, tự cài và mở lại. Bản macOS `.app` thì launcher
mở trang này để bạn tải tay.

---

Ghi chú các bản trước: [CHANGELOG.md](https://github.com/JunXmas/NostalgiaLauncher/blob/main/CHANGELOG.md)
