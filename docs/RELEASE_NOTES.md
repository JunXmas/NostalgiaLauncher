# Nostalgia 1.2.0rc33 — P2P nối lại, cài mod gọn hơn

Bản vá tập trung vào phòng chơi, đồng bộ modpack và việc cài nội dung vào đúng bản chơi. Launcher cũng giảm lượng log giữ trong RAM và giảm tải giao diện khi Minecraft đang chạy ở nền.

## Phòng chơi và đồng bộ modpack

- **Sửa bắt tay P2P khi giờ host lệch:** thời hạn dùng đồng hồ đơn điệu, giữ giới hạn cấp quyền và chống phát lại. Đồng hồ hệ thống lệch không còn làm host âm thầm bỏ yêu cầu kết nối.
- **Tiếp tục file đang đồng bộ:** nếu kênh ngắt giữa file, thử lại khối còn thiếu thay vì bỏ phần đã nhận. Kênh được gia hạn giữa các khối và kiểm tra lại quyền Premium trên máy chủ; file chỉ được cài sau khi khớp kích thước và SHA-256.
- **Đường truyền chậm có thể tiếp tục:** giới hạn chờ áp dụng cho từng khối, thay vì cắt cả file sau 30 giây dù vẫn tải được dữ liệu.
- **Biết đang chờ bước nào:** vào phòng, nối hai máy và mở world LAN có trạng thái riêng. Phân biệt phòng đóng/khóa, host chưa trả lời, dịch vụ bận và lỗi đường P2P. Nút **Thử kết nối lại** giữ phòng, cổng kết nối và bản chơi đã đồng bộ.
- **Giữ kết nối đang hoạt động:** lỗi đọc lobby tạm thời không làm mất world khi kênh P2P vẫn còn hoạt động. Không tự thương lượng liên tục khi kết nối thất bại.

## Cài mod đơn giản hơn

- Chọn bản chơi muốn cài, launcher tự chọn bản mod ổn định mới nhất tương thích với Minecraft và loader của bản chơi đó.
- Mở **Đổi phiên bản** khi muốn chọn bản khác; lựa chọn thủ công được giữ khi làm mới thông tin. Nút cài nêu rõ lý do nếu chưa chọn bản chơi hoặc không có bản tương thích.
- Shader và gói tài nguyên cũng lọc theo Minecraft của bản chơi đã chọn. Kết quả tìm kiếm đến muộn không ghi đè tab thư viện mới.

## Giao diện, hiệu năng và cosmetic

- Giới hạn log trong RAM, kể cả khi UI chưa kịp đọc; log đầy đủ trên đĩa vẫn được giữ để chẩn đoán game.
- Khi Minecraft chạy và launcher ở nền, giảm tải mica, nền thẻ, skin xoay và quán tính cuộn. Thu hồi tài nguyên khi thu nhỏ cửa sổ; icon/key art giải mã ở kích thước có giới hạn.
- Danh sách yêu cầu kết bạn dài chỉ dựng các ô gần màn hình. Nút bị khóa hiển thị lý do và hướng xử lý bằng tiếng Việt/English.
- Thêm cosmetic Halloween **Đèn bí ngô / Pumpkin Lantern**: khung avatar và nền hồ sơ rừng đêm, có xem thử và kiểm quyền trên máy chủ.
- Thông báo lỗi chứng chỉ HTTPS dễ hiểu hơn, phân biệt lỗi thời hạn với các lỗi chứng chỉ khác. Giữ xác minh TLS; không thử lại gửi mật khẩu khi chứng chỉ bị từ chối.

## Cách cùng chơi

1. **Cả host và khách cập nhật rc33.** Host vào **Bạn bè → Phòng chơi**, chọn bản chơi, tạo phòng rồi mời bạn.
2. Host khởi chạy Minecraft, vào world và chọn **Esc → Open to LAN → Start LAN World**. Launcher tự nhận cổng LAN.
3. Khách chọn nội dung modpack nếu có, xác nhận cảnh báo và hoàn tất đồng bộ. Khi đường P2P và world sẵn sàng, bấm **Khởi chạy & vào world**. Giữ launcher mở trong lúc chơi.
4. Khi có nút **Thử kết nối lại**, thử lại ngay trong phòng. Phòng đã đóng cần nhận lời mời mới. Khi không đồng bộ, hai bên vẫn cần Minecraft, loader và bộ mod tương thích.

## Kiểm tra và giới hạn

Đã kiểm thử ICE/DTLS thật trên loopback với đồng hồ host lệch, ngắt giữa file, file chậm hơn 30 giây, dữ liệu bị sửa và quyền Premium bị thu hồi. Ba luồng host/khách chạy ở hai tiến trình riêng qua backend HTTPS/WSS cục bộ đều truyền dữ liệu Minecraft thành công, cả bật lẫn tắt đồng bộ. Các kiểm thử backend và UI native cũng đạt.

Đây chưa phải xác minh Minecraft đầy đủ giữa hai nhà mạng. Mạng chặn UDP hoặc NAT không hỗ trợ đường trực tiếp vẫn có thể ngăn P2P. Relay dữ liệu tiếp tục **tắt**; không tự dùng tunnel hoặc TURN. Nếu còn lỗi, gửi Nhật ký launcher và phần cuối log game của cả host lẫn khách để phân biệt lỗi mạng, tài khoản và bộ mod.

Bản vá thông báo TLS không thể sửa chứng chỉ hết hạn của dịch vụ Ely.by; phía dịch vụ cần thay chứng chỉ. Bản phát hành dùng quyền Premium thật, không chứa cơ chế Ultimate TEST.

## Gói phát hành

- **Windows x64:** bộ cài và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

File đính kèm chỉ gồm bộ cài, gói portable/cập nhật và `SHA256SUMS`; không có ảnh preview hay tài liệu nội bộ.
