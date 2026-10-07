# Nostalgia 1.2.0rc8 — hướng dẫn thử Google-only (chuẩn bị)

Mã preview dành cho chủ dự án xem trước; chưa có bộ cài/draft rc8.
Giữ giao diện/mica/skin 3D, nhận diện modpack và cuộn quán tính của rc7.

## Thay đổi của rc8

- Người chơi không nhập URL hay mã Google. Nút **Tiếp tục với Google** mở trình duyệt,
  launcher tự nhận phiên và danh tính Nostalgia; tài khoản Minecraft vẫn độc lập.
- Địa chỉ Google/relay được đóng gói lúc build từ variable do chủ dự án cấu hình.
  Nếu chưa có backend, hiển thị Google chưa khả dụng, không mở địa chỉ giả.
- Hủy ở Google được báo về launcher; nếu trình duyệt không mở, có nút Mở lại Google.
- **Plus tạm khóa**: không tạo đơn, không thanh toán payOS, không lập/áp phương án sửa
  mod Plus, không đồng bộ modpack Plus, không hồ sơ/huy hiệu/preview Plus.
- Free kiểm tra xung đột mod vẫn hoạt động. Ủng hộ tùy tâm không kích hoạt Plus.
- Backend cũng khóa API Plus và quyền relay theo PLUS_ENABLED=false; sửa cờ UI
  không làm server cấp quyền. Mã backend rc8 cần triển khai riêng vào staging.

## Trạng thái Google thật

Workspace chưa có OAuth client hoặc backend Google được triển khai/cung cấp.
Bộ kiểm thử dùng Google giả tại biên mạng, HTTPS/Qt/RSA/D1 thật.
**Chưa xác minh đăng nhập Google production.**

Chủ dự án thiết lập theo [GOOGLE_SETUP.md](GOOGLE_SETUP.md), rồi cấu hình GitHub
variables NOSTALGIA_ACCOUNT_URL và NOSTALGIA_ROOM_SYNC_URL trước bản build tiếp theo.
Không đưa Client Secret/khóa payOS vào launcher hoặc git. Người chơi không cần tự setup.

## Thử trên máy của bạn

1. Tải setup.exe Windows, DMG đúng CPU macOS, hoặc AppImage/tar.gz Linux;
   so SHA-256 với SHA256SUMS. Draft chưa ký chứng chỉ hệ điều hành.
2. Mở lần đầu: màn hình đăng nhập phóng to. Google chưa cấu hình phải hiện lý do rõ,
   tài khoản Microsoft/Ely.by/ngoại tuyến vẫn dùng như trước.
3. Cài đặt không còn ô nhập endpoint. Mục Ủng hộ báo Plus tạm khóa, không có QR
   hay nút tạo đơn Plus. Quét mod miễn phí vẫn dùng, không có nút lập phương án Plus.
4. Thử quản lý bản chơi, modpack, nhận diện tên mod offline; bật/tắt và tháo mod;
   cài Forge 1.20.1 bản 47.4.23 rồi khởi chạy trên máy của bạn.
5. Cuộn bằng chuột/trackpad/kéo thả; thử cửa sổ 1024×600, chữ 150%, Giảm chuyển động.
6. Skin: xoay 3D và thử đổi skin Microsoft/Ely.by thật bằng tài khoản của bạn.
   Vòng rc8 không sửa auth/upload skin Minecraft.
7. Sau khi Google staging sẵn sàng và được đóng gói: thử tester login, hủy đăng nhập,
   mở lại launcher, đổi máy, thêm bạn/chat. Máy đầu mất phiên dịch vụ khi máy thứ hai login.
8. Thử LAN/lời mời chỉ khi relay/binding staging đã sẵn sàng; Plus pack sync vẫn khóa.

Các ảnh rc8 chụp từ Qt thật; tài khoản Google chưa kết nối. Không có token/secret trong ảnh.
Xem RC8_VALIDATION.md cho kiểm thử và giới hạn. Vòng rc8 chưa build/smoke
Windows/macOS, chưa kiểm GUI trên phần cứng thật của người dùng.

**Chưa build/tạo draft rc8.** Các bước tải bộ cài chỉ áp dụng sau khi chủ dự án yêu cầu build.
