# Google-only preview rc8 — chưa build bộ cài/tạo draft

Client trên nhánh `preview/glass-review`; backend private tại
`e3d50999bd70919729a05abb56443602950721ed`, nhánh `preview/google-plus-rc2`.
Theo yêu cầu chủ dự án: không tạo tag/release rc8, không build bộ cài, không publish,
không merge main hoặc deploy backend.

## Thay đổi

- Chủ dự án tích hợp endpoint vào bản build; người chơi không nhập URL/mã Google.
  Khi chưa có endpoint thật, Google hiển thị chưa khả dụng.
- Giữ OAuth trình duyệt + PKCE/state/nonce, nhận phiên tự động và tài khoản Minecraft
  độc lập. Thêm xử lý hủy consent/lỗi mở trình duyệt.
- Runtime khóa Plus/payment/repair gateway, ẩn upsell và đồng bộ modpack Plus.
  Free quét xung đột mod còn dùng; bạn bè/chat dùng danh tính Google.
- Backend PLUS_ENABLED thiếu/false đều chặn API Plus/payment/profile và quyền
  authorizer, không chỉ ẩn UI; không xóa entitlement đã lưu.
- Menu phiên bản còn tối đa 6 dòng, có tìm kiếm cho danh sách dài, dùng index gốc
  để chọn đúng bản cài. Chiều cao không vượt 48% cửa sổ, tự đặt lên/xuống.
- Nền kính lấy ảnh từ popup phía dưới, không lấy lại chính menu; vùng capture theo
  vị trí thực sau khi mở/đổi kích thước, blur được giới hạn trong khung menu.
  Software renderer dùng nền tint dễ đọc; tôn trọng Giảm chuyển động.
- Giữ nhận diện mods, cuộn quán tính, mica và skin 3D của rc7.
- Chỉ định PNG khi đọc texture/colormap Minecraft để tránh Qt dò plugin SVG trong
  luồng nền và khóa chéo Qt/GIL; không đổi model hay texture Minecraft.

## Kiểm thử

- Backend: **22 passed**, workerd/D1/R2 thật; Google/payOS giả tại biên mạng.
  Chặn GET/POST Plus dù DB đã có entitlement; authorizer không cấp quyền. Luồng
  Google, bạn bè/chat và thu hồi phiên máy cũ vẫn qua kiểm thử.
- Full client software: **1 failed, 1414 passed, 7 skipped, 1 deselected**, 278,19s.
  Lỗi duy nhất là tên biến trong test menu mới trái GLOSSARY. Đã đổi sang tên chuẩn;
  kiểm tra AST quy ước tên qua. Kết quả chạy lại nhóm quy ước/UI ghi bên dưới.
  Không ghi lượt full này thành “toàn bộ passed”. Các test mạng/game thật vẫn bị
  loại/bỏ qua theo mặc định của repository.
- Kiểm tra trọng tâm client trước sửa PNG: **26 passed**, có OAuth HTTPS và QTimer
  tự nhận phiên; snapshot mua đứt giả không mở Plus/payment/repair.
- Block/texture/notifier sau sửa PNG: **26 passed**, 7,10s.
- OpenGL trước căn chỉnh kính cuối: **58 passed**, 47,26s.
- OpenGL + toàn bộ nhóm quy ước sau sửa tên/căn chỉnh kính cuối: **65 passed**,
  48,18s. Menu khớp vùng backdrop, không tràn, tìm kiếm trả đúng index ở 100%/150%.
- Ruff check, format check, mypy (477 source/test files), uv lock, git diff check qua.

Hai lượt full trước bị dừng: một lượt treo ở Qt GC/dò SVG (đã lưu stack native);
ứng viên sửa đầu dùng bytes cho format nhưng binding PySide thực tế nhận str,
đã sửa lại. Không tính hai lượt bị dừng là pass.

## Preview

Ảnh Qt thật ở `docs/preview/rc8/`, kiểm cửa sổ 1440×900 và 1024×600/chữ 150%.
Ảnh Google chưa kết nối, không dùng token/account giả để trông như production.
Ảnh menu dùng metadata công khai Fabulously Optimized tải qua Modrinth API ngày
07/10/2026, 474 bản phát hành; không cài pack trong quá trình chụp.
Các lượt chụp kiểm tra không có QML warnings. Ảnh PNG không phải phép đo FPS.

## Giới hạn

Chưa có OAuth client/backend production được cung cấp hoặc triển khai. Chưa thử
Google thật, keyring Windows/macOS, game/Forge/LAN nhiều máy hoặc giao dịch ngân hàng.
OpenGL chạy qua Mesa/Xorg ảo; chưa đo FPS trên GPU của người dùng.
Không có CI build, bộ cài hay smoke Windows/macOS mới cho rc8.

Hướng dẫn chủ dự án: [GOOGLE_SETUP.md](GOOGLE_SETUP.md).
Phương án Vietcombank cá nhân: [PAYMENT_ALTERNATIVES.md](PAYMENT_ALTERNATIVES.md).
