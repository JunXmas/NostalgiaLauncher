Launcher **nhìn khác hẳn** so với 1.0.

Bảy trang trước đây nhìn như một trang: cùng một sắc lục dùng ở 94 chỗ, mỗi trang tự quyết
cỡ chữ và kiểu tiêu đề của riêng nó. Bản này làm lại từ bảng màu trở đi.

## Giao diện

- **Mỗi tab một màu.** Bảy sắc lấy từ chính khối icon của mục đó; nền pha 6% màu tab và
  chuyển mượt khi bạn đổi trang.
- **Font đóng kèm**: Inter cho chữ đọc, Minecraft F2D cho nhãn viết hoa — cả hai có đủ dấu
  tiếng Việt. Bo góc về 0, thẻ vẽ bằng cạnh vát, như minecraft.net.
- **Khối Minecraft xoay** ở thanh bên khi rê chuột — tăng tốc dần rồi rung từng cơn, rời
  chuột thì hãm lại. Texture lấy từ jar client của chính bạn.
- **Thẻ bản chơi nổi lên** thay vì nằm phẳng: nét mực dày, ô ảnh khoét lõm, trỏ vào thì nhấc
  lên.
- **Thanh bên vẽ đầu nhân vật của bạn** từ file skin, thay cho một chữ cái trên nền màu.

## Tạo bản chơi & trang chủ

- Bản **"Tối ưu hiệu năng"** là thẻ riêng, có chip ĐỀ XUẤT và được chọn sẵn. Năm loader còn
  lại vẫn hiện đủ ngay dưới; chỉ RAM và thư mục gập vào "Thiết lập nâng cao".
- Chọn phiên bản không hỗ trợ **không còn bị xoá ngầm lựa chọn của bạn**. Nút tạo bị chặn,
  dòng "Còn thiếu" nói vì sao, và có nút đưa bạn sang loader dùng được.
- Trang chủ bỏ sáu thẻ dẫn tới đúng những trang thanh bên đã dẫn tới (và che mất ảnh nền).
  Chưa có tài khoản hay bản chơi thì khối CHƠI nói thiếu gì và đưa luôn nút đi làm việc đó.

## Tài khoản & skin Ely.by

- **Hỗ trợ skin tải sẵn ngay lúc đăng nhập**, không đợi tới lúc bấm CHƠI. Hàng tài khoản báo
  "Skin trong game: đang tải hỗ trợ…" khi chưa xong. Mạng hỏng thì bạn mất skin chứ không mất
  buổi chơi.
- **Nút Dùng** hiện trên mọi hàng tài khoản chưa chọn. Trước đây bấm cả hàng vẫn chuyển được
  nhưng không có gì nói ra.
- **"Đăng ký ↗"** cạnh nút đăng nhập Ely.by, và **"Đổi skin ở ely.by ↗"** cho tài khoản Ely.
  Launcher không upload skin lên Ely.by được (khác Microsoft), nên "Thêm skin" chỉ đổi ảnh
  launcher hiện — người chơi khác trong game vẫn thấy skin cũ cho tới khi bạn đổi ở ely.by.
- Sửa: nút "Thêm skin" lọt ra ngoài ô. Sửa: bấm DỪNG thì cửa sổ tự thu nhỏ.

## Giấy phép đổi sang AGPL-3.0

Điều 13 của AGPL buộc ai chạy bản đã sửa **cho người khác dùng qua mạng** cũng phải mở mã.
Kho có relay chơi chung; nếu chỉ GPL thì một bản fork đóng mã chạy trên máy chủ được mà không
vi phạm gì. Mọi dòng chạy trên máy bạn vẫn công khai như cũ.

## Tải xuống

| Nền tảng | File | Ghi chú |
|---|---|---|
| Linux (mọi bản) | `nostalgia-1.1.0-linux-x64.AppImage` | `chmod +x`, bấm đúp. Cần glibc ≥ 2.35 (Ubuntu 22.04+, Debian 12+, Mint 21+, Fedora 36+, Arch). |
| Debian / Ubuntu / Mint / Pop!_OS | `nostalgia_1.1.0_amd64.deb` | `sudo apt install ./nostalgia_1.1.0_amd64.deb` |
| Fedora / openSUSE / RHEL / Nobara | `nostalgia-1.1.0-1.x86_64.rpm` | `sudo dnf install ./nostalgia-1.1.0-1.x86_64.rpm` |
| Linux, xách tay | `nostalgia-1.1.0-linux-x64.tar.gz` / `.zip` | giải nén, chạy `Nostalgia/nostalgia-ui` |
| macOS Apple Silicon | `nostalgia-1.1.0-macos-arm64.dmg` | kéo vào Applications; lần đầu: chuột phải → Open (chưa ký) |
| macOS Intel | `nostalgia-1.1.0-macos-x64.dmg` | như trên |
| Windows 10/11 x64 | `nostalgia-1.1.0-windows-x64-setup.exe` | bộ cài, không cần quyền admin; SmartScreen → "More info → Run anyway" (chưa ký) |
| Windows, xách tay | `nostalgia-1.1.0-windows-x64.zip` | giải nén, chạy `Nostalgia\nostalgia-ui.exe` |

Nhớ đối chiếu `SHA256SUMS` với file tải về — bộ tự cập nhật cũng đối chiếu đúng file này
trước khi cài, và tải về đúng loại gói bạn đang dùng.

## Cách cập nhật

Mở launcher là nó tự kiểm sau vài giây; có bản mới thì dải màu hiện ngay trên đầu, bấm
"Cập nhật ngay" rồi để yên — launcher tự tải, tự cài và mở lại. Bản macOS `.app` thì launcher
mở trang này để bạn tải tay.

## Chưa kiểm được

Skin Ely.by hiện trong game dựa vào authlib-injector (javaagent JVM, không phải mod).
Launcher tải và tiêm đúng, jar khớp sha256 upstream — nhưng **chưa có lần chạy Minecraft
thật nào để xác nhận skin hiện lên trước mắt người chơi khác.** Ai thử được thì báo lại giúp.
