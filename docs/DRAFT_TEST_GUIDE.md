# Nostalgia 1.2.0rc6 — hướng dẫn thử draft

Bản này dành cho chủ dự án thử trước khi publish. Không thay bản ổn định và không
phát qua auto-update. Dùng một thư mục dữ liệu mới hoặc sao lưu thư mục đang chơi.

## Mã đã tích hợp

- Giao diện mới mặc định, giữ palette cũ, thẻ mica và model block Minecraft.
  Lần mở đầu phóng to cửa sổ đăng nhập; trang bạn bè thu gọn theo kích thước cửa sổ.
- Quản lý bản chơi mới chia Tổng quan / Nội dung đã cài / Hiệu năng / Sao lưu & dữ liệu.
  Tab Đã cài và bộ lọc không mở lại trang thư viện cũ; nút và form dùng theme mới.
- Manrope cho tiêu đề, Inter cho chữ đọc, block sidebar xoay trở lại, chuyển trang/popup
  có animation; cuộn theo tham số Lenis của Skew và thiết lập Giảm chuyển động.
- Popup thêm tài khoản, mã Microsoft và cài modpack lấy đúng nội dung trang phía sau để làm mica.
- Skin/Cape hiển thị skin 3D đúng UV Steve/Alex; kéo hoặc dùng phím để xoay 360°.
  Thẻ skin trong kho dùng ảnh nhân vật 3D, chỉ nạp khi vào vùng nhìn; đứng yên không có timer render.
- Thư viện có popup dự án và chọn phiên bản cho mod, resourcepack, shader, modpack.
- Tài khoản Google riêng cho Plus/bạn bè/chat/lời mời. Phiên mới thu hồi phiên dịch vụ
  cũ; tài khoản Minecraft vẫn dùng để khởi chạy game. Không đăng xuất Gmail trên máy khác.
- Plus: tháng 29.000đ; 6 tháng 69.000đ; năm 109.000đ; mua đứt 209.000đ.
  Gói 6 tháng trở lên có màu hồ sơ và huy hiệu; năm/mua đứt có link preview riêng.
- Thanh toán payOS: QR tạo trong launcher, khôi phục đơn đang chờ, xác nhận bằng server.
  Nút kiểm tra chuyển khoản không tự cấp Plus. Giá và thời hạn do server quyết định.
- Free quét metadata Fabric/Forge/NeoForge: thiếu phụ thuộc, ID trùng, sai loader,
  khoảng phiên bản hoặc khai báo xung đột. JAR hỏng/cú pháp chưa hiểu báo chưa xác minh.
- Plus lập phương án hỗ trợ: tắt file trùng/sai loader/xung đột được khai báo, bổ sung
  một số phụ thuộc từ Modrinth. Hiển thị thay đổi trước khi áp dụng, kiểm hash tải về,
  quét lại, sao lưu và hoàn tác sau khi mở lại launcher. Không sửa thế giới chơi.

## Phần cần dịch vụ thật

Mã backend nằm trong kho private `JunXmas/nostalgia-backend`, nhánh review tương ứng.
Chưa deploy dịch vụ hoặc cấu hình khóa Google/payOS trong lượt này. Bộ cài không chứa
khóa bí mật, dữ liệu demo hoặc cách tự mở Plus bằng cờ local.

Khi chưa cấu hình endpoint, giao diện và game local vẫn dùng được; Google, thanh toán,
bạn bè, sửa mod Plus và đồng bộ pack qua dịch vụ chưa dùng được. Trong Cài đặt có ô
URL tài khoản và relay HTTPS dành cho draft; lưu rồi khởi động lại launcher. Có thể dùng
biến môi trường `NOSTALGIA_ACCOUNT_URL`, `NOSTALGIA_ROOM_SYNC_URL` thay thế.
Chỉ dùng URL do chủ dự án cung cấp, không nhập secret/token vào các ô này.

Backend cần Google OAuth Web client với callback `/v1/auth/google/callback`, shared D1,
R2 private, các service bindings, INVITE_KEY và ba secret payOS. Đăng ký webhook
`/v1/payments/payos/webhook`. Kênh preview cần upload artifact vào R2 và thêm metadata
`preview_builds` trước khi link tải dùng được. Hướng dẫn staging ở kho private.

## Các bước thử trên máy của bạn

1. Windows: tải `setup.exe`; Linux: AppImage hoặc tar.gz; macOS: DMG đúng CPU.
   So SHA-256 với `SHA256SUMS`. Đây là draft chưa ký chứng chỉ hệ điều hành.
2. Mở lần đầu, đăng nhập Minecraft/ngoại tuyến, kiểm Home, Thư viện, bản chơi, Cài đặt.
   Thử cửa sổ 1024×600 và chữ 150%; cuộn tới các thao tác nếu nội dung dài.
   Mở quản lý bản chơi, lưu tên/RAM, thử Đã cài, bật/tắt một mod rồi bật lại.
   Hover/focus sidebar, chuyển trang, mở/đóng popup; bật Giảm chuyển động.
   Cuộn bằng chuột/trackpad, đảo hướng và kéo scrollbar; xem GIF preview đính kèm để đối chiếu.
   Vào Skin, kéo nhân vật để xoay, dùng ← →, đổi Slim/Wide và cuộn kho nhiều skin.
   Đóng/thu nhỏ cửa sổ rồi mở lại: skin phải hiện lại và giữ đúng tài khoản.
3. Cài Forge 1.20.1 số ngắn `47.4.23`, rồi một modpack Forge. Khởi chạy game để kiểm
   cài đặt thực tế; fixture của CI không thay thế bước này.
4. Bản chơi → quản lý → Sao lưu & dữ liệu → Kiểm tra xung đột mod. Quét bộ mod bình thường, thử hai JAR có
   cùng ID và một mod thiếu phụ thuộc. Quét phải chỉ đọc, không đổi file.
5. Với dịch vụ staging và Plus: lập phương án, xem danh sách, áp dụng rồi hoàn tác.
   Sửa file mod sau khi áp dụng: hoàn tác phải từ chối ghi đè thay đổi đó.
6. Hai máy: đăng nhập cùng Google trên máy thứ hai; máy đầu phải mất phiên dịch vụ.
   Plus/bạn bè vẫn theo tài khoản. Kiểm nhận lời mời, chat, mở LAN, vào phòng.
7. Host Plus chia sẻ modpack; khách Free được mời phải nhận ô đồng bộ và một bản chơi
   riêng. Kiểm đổi phiên host/thu hồi Plus làm link dịch vụ cũ bị từ chối.
8. payOS staging: chưa trả tiền thì bấm kiểm tra vẫn pending; đơn sai giá/sai người
   không cấp quyền; webhook lặp không gia hạn thêm. Thử QR, đơn hết hạn và mở lại app.

## Giới hạn kiểm chứng

Checker dựa vào metadata, chưa phân tích crash log hoặc mọi tương tác lúc game chạy;
không hứa sửa mọi xung đột. Nguồn phụ thuộc tự bổ sung hiện giới hạn Fabric API,
Architectury, Cloth Config và Fabric Language Kotlin. Cú pháp/nguồn chưa hỗ trợ hoặc
phụ thuộc mới còn thiếu làm tác vụ dừng trước khi thay mod đang dùng.

Quyền dịch vụ được kiểm ở server. Không thể bảo đảm chống can thiệp tuyệt đối trên
máy người dùng; bearer có thể bị sao chép và pack đã tải có thể chép thủ công.
Mua đứt không hết hạn trong thời gian dịch vụ hoạt động, không bao gồm hosting hoặc
hỗ trợ không giới hạn. Chưa triển khai tự gia hạn, hoàn tiền tự động hoặc quản trị đơn.

Kiểm thử tự động dùng HTTPS cục bộ và Worker/D1/R2 thật với Google/payOS giả ở biên
mạng. Chưa xác minh OAuth/thu tiền production hoặc Minecraft nhiều máy. Các build CI
chạy smoke-test bộ đóng gói, không phải một phiên chơi Minecraft trên từng hệ điều hành.
