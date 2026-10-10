# Room, mời bạn và truyền trực tiếp

Luồng host: chọn bản chơi → Tạo room → đợi chuẩn bị/chia sẻ → Mời vào room →
Khởi chạy Minecraft → mở world → Esc / Open to LAN / Start LAN World.

Luồng khách: Vào room → xem và chọn file modpack nếu có → xác nhận cảnh báo →
đợi host mở LAN → Khởi chạy & vào world. Bản chơi đã đồng bộ được chọn tự động.
Nếu host không chia sẻ pack, khách chọn một bản chơi đã cài tương thích.

Nhắn tin là tùy chọn thu gọn mặc định. Chọn bạn không tải tin nhắn; chỉ mở khung
nhắn tin mới bật polling chat. Khi đổi trang hoặc thu gọn, polling chat dừng.

## Chi phí và tương thích

- WebRTC ưu tiên dữ liệu game và file custom đi trực tiếp; không phải VPN cả máy.
- Public mods vẫn lấy từ nguồn chính thức. File custom dùng kênh sync trực tiếp có
  hạn quyền do backend cấp, kiểm size/hash; không nối được thì dùng relay HTTPS cũ.
- Thông tin phòng chờ được đọc mỗi 15 giây; khi world mở, giảm xuống 60 giây.
  Endpoint lobby không đọc/ghi D1. Phòng không chia sẻ pack dừng polling manifest.
- Không loại bỏ dịch vụ tài khoản/bạn bè hoặc signaling; không hứa chi phí bằng 0.
- Backend cần bản có `/v1/rooms/:id/lobby` và `/peer`. Client cũ giữ được đường relay.
  Client mới dùng relay với backend cũ; không nhận được trạng thái lobby mới khi API chưa có.
- Bản này chưa cần quyền admin, TUN hay driver VPN. Mạng chặn UDP/CGNAT dùng relay.
- Xem giới hạn bảo mật và kiểm thử ở `MULTIPLAYER_SECURITY.md`.

Các thay đổi này đang trong workspace để kiểm thử, chưa thuộc bản rc26 đã phát hành.
