Bản vá quan trọng: CHƠI CHUNG đã hoạt động trở lại.

Nếu bạn đang dùng 1.0.12 hoặc cũ hơn, hãy cập nhật — trước đây host mở "Open to LAN"
trong game rồi mà launcher vẫn báo không thấy world nào. Bản này cũng sửa skin Ely.by
luôn ra Steve/Alex, thêm nhập bản chơi từ TLauncher và SKlauncher, và bật Discord Rich
Presence trên Windows.

## Chơi chung (quan trọng nhất)

- **Dò "Open to LAN" không còn trượt.** Máy có nhiều card mạng (Wi-Fi + Ethernet + máy ảo
  Hyper-V/WSL, hay VPN) trước đây bị bỏ sót vì launcher chỉ nghe trên một card. Giờ nghe
  trên từng card một.
- **Báo lỗi nói đúng nguyên nhân.** Trước đây cổng bị chiếm và "chưa ai mở LAN" ra cùng
  một câu, nên bạn được khuyên làm đúng cái vừa làm. Giờ hai tình huống nói hai câu khác
  nhau.
- **Chống spam ở máy chủ phòng đã bật thật.** Giới hạn số lần vào phòng trước đây khai rồi
  nhưng không ai gọi.

## Skin

- **Skin Ely.by hiện lại được.** Trước đây mọi tài khoản Ely luôn ra Steve/Alex vì launcher
  gọi địa chỉ `http://` rồi tự từ chối chính mình.
- **Đổi skin trên tài khoản Microsoft** kiểm kích thước ảnh trước khi gửi, và làm mới phiên
  đăng nhập nên không còn báo "Mojang từ chối skin" oan.
- **Skin tự chọn không bị ghi đè** mỗi lần launcher đồng bộ với máy chủ.

## Nhập bản chơi từ launcher khác

- **Thêm TLauncher và SKlauncher.** Ai đang chuyển từ launcher lậu sang thì bản chơi cũ,
  mod, thế giới và gói tài nguyên mang sang được. Thư mục nguồn chỉ được ĐỌC, không sửa
  không xoá — bạn vẫn dùng launcher cũ song song trong lúc chuyển.
- Tổng cộng nhập được từ 6 launcher: PrismLauncher, CurseForge, ModrinthApp, Vanilla,
  TLauncher, SKlauncher.

## Giao diện

- **Thanh chọn bản chơi mở sẵn bản bạn vừa chơi**, và cho thấy còn bản khác — trước đây
  trông như chỉ có một bản.
- Nút gạt bật/tắt vẽ lại thành khối vuông kiểu Bedrock, thêm thanh trượt.

## Discord

- **Discord Rich Presence chạy trên Windows.** Trước đây phần Windows mới chỉ là chỗ trống.
  Bật ở CÀI ĐẶT, cần dán Application ID của bạn.

## Tải xuống

| Nền tảng | File | Ghi chú |
|---|---|---|
| Linux (mọi bản) | `nostalgia-1.0.14-linux-x64.AppImage` | `chmod +x`, bấm đúp. Cần glibc ≥ 2.35 (Ubuntu 22.04+, Debian 12+, Mint 21+, Fedora 36+, Arch). |
| Debian / Ubuntu / Mint / Pop!_OS | `nostalgia_1.0.14_amd64.deb` | `sudo apt install ./nostalgia_1.0.14_amd64.deb` |
| Fedora / openSUSE / RHEL / Nobara | `nostalgia-1.0.14-1.x86_64.rpm` | `sudo dnf install ./nostalgia-1.0.14-1.x86_64.rpm` |
| Linux, xách tay | `nostalgia-1.0.14-linux-x64.tar.gz` / `.zip` | giải nén, chạy `Nostalgia/nostalgia-ui` |
| macOS Apple Silicon | `nostalgia-1.0.14-macos-arm64.dmg` | kéo vào Applications; lần đầu: chuột phải → Open (chưa ký) |
| macOS Intel | `nostalgia-1.0.14-macos-x64.dmg` | như trên |
| Windows 10/11 x64 | `nostalgia-1.0.14-windows-x64-setup.exe` | bộ cài, không cần quyền admin; SmartScreen → "More info → Run anyway" (chưa ký) |
| Windows, xách tay | `nostalgia-1.0.14-windows-x64.zip` | giải nén, chạy `Nostalgia\nostalgia-ui.exe` |

Nhớ đối chiếu `SHA256SUMS` với file tải về. File `.zip` là thứ bộ tự cập nhật tải.

## Cách cập nhật

Mở launcher là nó tự báo sau vài giây, vào CÀI ĐẶT → CẬP NHẬT bấm tải. Bản đóng gói
Linux/Windows tự cài và mở lại. Bản `.deb`/`.rpm`/AppImage/macOS `.app` thì launcher mở
trang này để bạn tải tay.

---

Ghi chú các bản trước: [CHANGELOG.md](https://github.com/JunXmas/NostalgiaLauncher/blob/main/CHANGELOG.md)
