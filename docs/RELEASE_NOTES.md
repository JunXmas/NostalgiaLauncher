# Nostalgia 1.2.0rc31 — Chuẩn bị xong, cùng vào world

Bản vá này tập trung vào phòng chơi chung: giữ modpack đã chuẩn bị ổn định, nhận cổng LAN chắc chắn hơn và đợi host mở khóa trước khi kết nối.

## Những lỗi đã sửa

- **Không chuẩn bị modpack lặp lại:** cập nhật trạng thái khóa phòng đến muộn từng khiến modpack đã sẵn sàng được chia sẻ lại. Phòng giờ giữ snapshot hoàn tất để bạn mời bạn bè và khởi chạy game.
- **Nhận LAN từ đúng bản chơi:** launcher đọc thông báo từ stdout và `latest.log`, hỗ trợ log có màu, bỏ cổng của phiên chơi trước và theo dõi log xoay vòng. Cổng vẫn phải trả lời kiểm tra Minecraft trước khi phòng báo world sẵn sàng.
- **Đợi host chuẩn bị xong:** khách không thương lượng P2P lúc phòng đang khóa để chia sẻ nội dung, tránh bị từ chối ngay trước khi host mở phòng. World đang khóa cũng không được hiện là sẵn sàng.
- **Theo dõi log nhẹ:** đọc trên luồng nền, giới hạn 64 KiB/lần, bỏ thông báo trùng và dừng khi game đóng.

## Cách cùng chơi

1. Host vào **Bạn bè → Chơi chung**, chọn bản chơi và bấm **Tạo phòng**. Nếu bật đồng bộ, đợi modpack sẵn sàng rồi mời bạn.
2. Host bấm **Khởi chạy**, vào world và chọn **Esc → Open to LAN → Start LAN World**. Giữ launcher mở trong lúc chơi.
3. Khách nhận lời mời, chọn nội dung cần đồng bộ nếu có, đợi P2P và world sẵn sàng rồi bấm **Khởi chạy & vào world**.

**Host và khách nên cùng cập nhật rc31.** Khi tắt đồng bộ, hai bên vẫn cần Minecraft, loader và bộ mod tương thích.

## Kiểm thử và giới hạn kết nối

Đã thử backend thật chạy cục bộ qua HTTPS/WSS với hai dịch vụ phòng độc lập: bật và tắt đồng bộ, nhận file resourcepack qua P2P, rồi gửi dữ liệu Minecraft qua nhiều kết nối trên cùng kênh. Có kiểm thử hồi quy cho cập nhật trạng thái đến muộn, phòng khóa, log cũ, log bị cắt/xoay và luồng Qt nhận cổng LAN.

Kiểm thử này xác minh giao thức trên máy cục bộ; chưa xác minh kết nối giữa hai nhà mạng thực tế. Mạng chặn UDP và một số kiểu NAT/CGNAT vẫn có thể ngăn P2P. **Relay dữ liệu tiếp tục tắt**, không có chuyển sang relay âm thầm. Thông tin thương lượng được bảo vệ bằng AES-GCM qua HTTPS/WSS; dữ liệu P2P dùng DTLS, file đồng bộ được kiểm SHA-256. Quyền Plus được kiểm tra trên máy chủ, không mở Ultimate TEST.

## Gói phát hành

- **Windows x64:** bộ cài và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

Cơ chế cập nhật giữ nguyên: launcher thông báo bản mới, tải và cài khi bạn chọn cập nhật; macOS mở trang tải. File đính kèm chỉ gồm bộ cài, gói portable/cập nhật và `SHA256SUMS`.
