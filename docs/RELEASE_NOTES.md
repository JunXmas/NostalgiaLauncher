# Nostalgia 1.2.0rc32 — World sẵn sàng, kết nối rõ ràng

Vào được room là bước đầu. Bản vá này giúp danh sách LAN và nút vào world phản ánh đúng đường kết nối game, đồng thời báo rõ hơn khi không thể bắt tay với host.

## Những lỗi đã sửa

- **World chỉ xuất hiện khi có thể kết nối:** máy khách từng quảng bá world trong LAN ngay khi vào room, dù host chưa mở world hoặc P2P chưa sẵn sàng. Launcher giờ đợi world sẵn sàng, phòng mở khóa và đường game đang hoạt động rồi mới quảng bá.
- **Cập nhật ngay khi P2P mất kết nối:** trạng thái world và nút vào game được cập nhật khi kênh đóng, thay vì giữ trạng thái sẵn sàng cho tới lần đọc lobby tiếp theo. Beacon LAN cũng kiểm lại đường kết nối ở mỗi lượt phát.
- **Lỗi bắt tay được báo trên launcher:** phân biệt chưa có đường P2P, không mở được kết nối và không hoàn tất bắt tay với host. Thông báo có cả tiếng Việt và tiếng Anh; log chẩn đoán không ghi mã phòng.
- **Giảm thao tác chờ khi nối game:** kết nối Minecraft qua loopback không phải tra DNS tên máy hoặc liệt kê card mạng trước khi bắt tay.

## Cách cùng chơi

1. **Cả host và khách cập nhật rc32.** Host vào **Bạn bè → Chơi chung**, chọn bản chơi, tạo phòng rồi mời bạn.
2. Host khởi chạy Minecraft, vào world và chọn **Esc → Open to LAN → Start LAN World**. Launcher tự nhận cổng LAN.
3. Khách hoàn tất đồng bộ nếu có, đợi trạng thái **Kết nối trực tiếp · DTLS** và world sẵn sàng rồi bấm **Khởi chạy & vào world**. Giữ launcher mở trong lúc chơi.
4. Nếu launcher báo mất P2P, rời room và nhận lại lời mời. Khi tắt đồng bộ, hai bên vẫn cần phiên bản Minecraft, loader và bộ mod tương thích.

## Kiểm tra kết nối

Đã tái hiện trên mã rc31 hai lỗi quảng bá LAN quá sớm và giữ trạng thái sẵn sàng sau khi peer đóng; kiểm thử hồi quy đạt sau bản sửa. Các bài kiểm tra dùng ICE/DTLS thật trên loopback, truyền byte game qua TCP proxy và xác nhận mất peer cập nhật trạng thái ngay.

Kết quả này chưa xác minh Minecraft đầy đủ giữa hai nhà mạng. Một số mạng chặn UDP hoặc NAT/CGNAT vẫn có thể ngăn P2P. Nếu Minecraft chỉ hiện **Disconnected**, hãy gửi phần cuối Nhật ký của cả host và khách để phân biệt lỗi truyền tải, tài khoản và modpack. Dữ liệu game và file custom tiếp tục đi qua P2P mã hóa; relay dữ liệu giữ trạng thái tắt.

## Gói phát hành

- **Windows x64:** bộ cài và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

File đính kèm gồm bộ cài, gói portable/cập nhật và `SHA256SUMS`.
