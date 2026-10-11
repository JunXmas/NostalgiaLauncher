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

## Thời hạn và phục hồi kết nối

- Backend cấp mỗi yêu cầu P2P tối đa 45 giây, chuyển qua WSS của đúng host.
  Host tính thời gian từ lúc nhận bằng đồng hồ đơn điệu; không so giờ Windows
  với giờ backend. Request ID được giữ 120 giây để chặn phát lại. Backend mới
  gửi `ttl_seconds=45`; backend cũ có `expires_at` dùng thời lượng mặc định 45 giây.
  Khách không được tự tăng thời lượng qua JSON: backend ghi đè các trường này.
- Kênh file gia hạn trước khối tiếp theo khi cửa sổ cũ đã hết. Backend kiểm tra
  lại manifest, lời mời và Premium của host. Không biến quyền 45 giây thành quyền
  không giới hạn. Ngắt giữa file thử lại khối đang thiếu một lần, giữ các khối đã
  nhận và chỉ trả file sau khi kiểm SHA-256. Hủy thao tác đóng kênh.
- Mỗi khối có tối đa 30 giây chờ; cả file có thể lâu hơn nếu vẫn tiến triển.
  Dữ liệu nhận từ phòng khác không được dùng lại kênh sync đã lưu.
- Thương lượng ICE, dịch vụ signaling và mở kênh có thời hạn riêng. Lỗi HTTP
  không bị gán nhầm thành lỗi UDP. Log ghi bước, mã HTTP, thời gian và loại lỗi,
  không ghi SDP, IP, mã phòng, invite proof hoặc token.
- Nút Thử kết nối lại áp dụng cho lỗi mạng, host chưa sẵn sàng hoặc dịch vụ bận.
  Phòng đã đóng cần lời mời mới. Không tự lặp thương lượng liên tục.

Kiểm thử hồi quy có hai đầu ICE/DTLS trên loopback: đồng hồ host lệch,
ngắt giữa file, file chậm hơn 30 giây, gia hạn quyền và từ chối khi Premium bị
thu hồi. Đây không phải kiểm chứng NAT giữa hai nhà mạng; P2P vẫn có thể bị
chặn trên mạng không hỗ trợ đường trực tiếp khi relay tắt.

## Nền relay giữ lại

`RoomService`, `JoinerBridge` và `HttpRoomSyncGateway` giữ cờ `relay_enabled`, mặc định
`False`. Các bài test nền dùng cờ `True` tường minh; luồng UI sản phẩm không bật cờ.
Backend khóa mặc định bằng `DATA_RELAY_ENABLED=false`. Khóa chặn socket game, socket
đang hibernation và HTTP GET/PUT file; P2P signaling, manifest và quyền Plus vẫn chạy.
Chỉ bật lại sau khi chủ dịch vụ quyết định cấp kinh phí và launcher được cấu hình lại.
