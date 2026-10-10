# Room, mời bạn và truyền trực tiếp

Luồng host: chọn bản chơi → Tạo room → đợi chuẩn bị/chia sẻ → Mời vào room →
Khởi chạy Minecraft → mở world → Esc / Open to LAN / Start LAN World.

Luồng khách: Vào room → xem và chọn file modpack nếu có → xác nhận cảnh báo →
đợi host mở LAN → Khởi chạy & vào world. Bản chơi đã đồng bộ được chọn tự động.
Nếu host không chia sẻ pack, khách chọn một bản chơi đã cài tương thích.

Nhắn tin là tùy chọn thu gọn mặc định. Chọn bạn không tải tin nhắn; chỉ mở khung
nhắn tin mới bật polling chat. Khi đổi trang hoặc thu gọn, polling chat dừng.

## Chi phí và tương thích

- P2P là đường dữ liệu duy nhất cho host và khách; không có tùy chọn relay trong UI.
  Người cùng phòng có thể biết IP trực tiếp của nhau.
- WebRTC ưu tiên dữ liệu game và file custom đi trực tiếp; không phải VPN cả máy.
- Public mods vẫn lấy từ nguồn chính thức. File custom dùng kênh sync trực tiếp có
  hạn quyền do backend cấp, kiểm size/hash; không nối được thì báo lỗi, không tải qua HTTP.
- Thông tin phòng chờ được đọc mỗi 15 giây; khi world mở, giảm xuống 60 giây.
  Endpoint lobby không đọc/ghi D1. Phòng không chia sẻ pack dừng polling manifest.
- Không loại bỏ dịch vụ tài khoản/bạn bè hoặc signaling; không hứa chi phí bằng 0.
- Backend cần bản có `/v1/rooms/:id/lobby` và `/peer`. Bản cũ không có P2P phải cập nhật
  để chơi chung; không thể thêm P2P từ xa vào một bản đã cài.
- Bản này chưa cần quyền admin, TUN hay driver VPN. Nếu UDP/NAT chặn P2P, kết nối
  sẽ thất bại. Không tự chạy ngrok, không cấp tunnel hoặc TURN miễn phí.
- Xem giới hạn bảo mật và kiểm thử ở `MULTIPLAYER_SECURITY.md`.

Các thay đổi này đang trong workspace để kiểm thử, chưa thuộc bản rc26 đã phát hành.

## Nền relay giữ lại

`RoomService`, `JoinerBridge` và `HttpRoomSyncGateway` giữ cờ `relay_enabled`, mặc định
`False`. Các bài test nền dùng cờ `True` tường minh; luồng UI sản phẩm không bật cờ.
Backend khóa mặc định bằng `DATA_RELAY_ENABLED=false`. Khóa chặn socket game, socket
đang hibernation và HTTP GET/PUT file; P2P signaling, manifest và quyền Plus vẫn chạy.
Chỉ bật lại sau khi chủ dịch vụ quyết định cấp kinh phí và launcher được cấu hình lại.
