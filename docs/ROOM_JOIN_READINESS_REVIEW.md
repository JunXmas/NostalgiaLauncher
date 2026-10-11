# Trạng thái world khi khách vào phòng — 2026-10-11

Ảnh người dùng báo Minecraft hiển thị `Failed to connect to the server / Disconnected`.
Ảnh chưa chứa lý do ở log host/khách, nên chưa kết luận nguyên nhân của lần chơi đó.

## Lỗi đã tái hiện trên rc31

- Khách phát beacon LAN ngay khi vào room, trước khi world/P2P sẵn sàng. Minecraft
  thấy mục LAN nhưng proxy chưa có đường game và đóng TCP khi người chơi chọn mục đó.
- Khi kênh P2P đóng, trạng thái world vẫn sẵn sàng cho tới lần đọc lobby tiếp theo,
  có thể tới 60 giây. Nút khởi chạy vẫn cho phép vào một đường đã mất kết nối.

Hai kiểm thử chạy trong tiến trình riêng với các module gốc tại `480c202` đều thất bại:
beacon phát quá sớm và tín hiệu mất kết nối không tới trước hạn ba giây. Các tệp nguồn
trong workspace không bị thay lại để thực hiện phép đối chiếu này.

## Thay đổi

Beacon chỉ phát khi khách có world sẵn sàng, phòng không khóa và đường game đang sống.
Mỗi lượt phát kiểm lại kênh để không tiếp tục quảng bá một world có P2P đã đóng.
Callback đóng PeerMux cập nhật trạng thái world ngay, dừng đọc lobby của kết nối đã mất
và báo người chơi vào lại phòng. Rời phòng chủ động không phát thông báo lỗi này.

Proxy báo riêng lỗi chưa có P2P, mở đường truyền và bắt tay với host; log không ghi mã
phòng hoặc nội dung ngoại lệ. Kết nối loopback không phải tra DNS tên máy/liệt kê card
mạng trước khi bắt tay. Thông báo mới có cả tiếng Việt và tiếng Anh.

Không bật relay dữ liệu, không thêm TURN, endpoint hay polling backend mới. Nền relay
chỉ hoạt động khi cờ cho phép đã được bật tường minh như trước.

## Kiểm tra và giới hạn

- 238 kiểm thử multiplayer, room/host/guest UI, log LAN, ngôn ngữ, kiến trúc, quy ước
  và website đạt. Ruff, định dạng và mypy đạt.
- Kiểm thử hồi quy dùng hai đầu aiortc/ICE/DTLS thật và TCP loopback: bắt tay bị từ
  chối được báo, byte game đi qua proxy, mất peer lập tức hủy trạng thái world sẵn sàng.
- Chưa chạy Minecraft đầy đủ giữa hai nhà mạng; chưa có log để xác minh tài khoản,
  loader/modpack hay nguyên nhân disconnect trên máy người dùng.
- Đây là bản sửa mã sau rc31, chưa đóng gói hoặc phát hành.
