# Nostalgia 1.2.0rc23 — Mời bạn dễ hơn, click đúng chỗ

rc23 sửa vệt trắng và những khoảng trống bất thường bạn gặp trong thư viện, bản chơi và hướng dẫn. Ảnh chưa tải vẫn có nền tối đồng nhất; ảnh tải xong giữ hiệu ứng mica quen thuộc.

## Cùng vào world, dễ hiểu hơn

**Gửi, nhận và từ chối lời mời** không còn bị khóa khi launcher cập nhật trạng thái bạn bè. Nếu chưa có phòng, nút trong chat đưa bạn đến chọn bản chơi để host. Launcher vẫn chờ LAN và nội dung chia sẻ sẵn sàng trước khi cho gửi lời mời.

Hướng dẫn **Mời bạn vào world** hiện ngay trong chat và bảng phòng, có GIF cùng nội dung Tiếng Việt / English:

1. Host chọn bản chơi và bấm **Host & khởi chạy**.
2. Trong world Minecraft: **Esc → Open to LAN → Start LAN World**.
3. Quay lại launcher, chờ phòng sẵn sàng, chọn bạn trực tuyến rồi **Mời chơi**.
4. Người nhận bấm **Vào phòng**, xem/đồng bộ modpack nếu có, rồi kết nối thế giới LAN trong Minecraft.

**Launcher luôn giữ mở khi game khởi chạy.** Tùy chọn tự ẩn vào khay đã được bỏ, kể cả khi cấu hình cũ từng bật. Bạn có thể tiếp tục chat và gửi lời mời; khi tự thu nhỏ cửa sổ, launcher không giành lại tiêu điểm lúc game dừng.

## Cài nội dung vào đúng bản chơi

Nút tải ở thư viện tổng hiển thị **Cài / Install**. Bấm vào sẽ mở popup để bạn chọn bản chơi đích và bản phát hành tương thích trước khi tải mod, shader hoặc resourcepack. Launcher không tự cài vào bản chơi đã được chọn từ trước. Nếu mở thư viện từ quản lý một bản chơi, đích cài vẫn cố định ở bản chơi đó.

## Chấp nhận lời mời kết bạn ngay

Nút **Chấp nhận** vẫn hoạt động khi danh sách bạn bè đang làm mới ở nền. Yêu cầu đến hiện sẵn để dễ tìm; thao tác kết bạn chỉ khóa trong lúc chính thao tác đó đang xử lý. Chặn gửi trùng và bỏ kết quả từ phiên tài khoản đã đổi hoặc bị thu hồi.

## Popup nhận đúng một lần bấm

- Sửa nút trong popup/menu kích hoạt cả nút ở trang phía sau.
- Menu tài khoản và danh sách chọn phiên bản chặn thao tác ở nền trong lúc mở.
- Nút nhận click riêng biệt; kéo từ nút để cuộn danh sách vẫn hoạt động, không kích hoạt nút khi kéo.
- Khung thêm tài khoản và cài modpack chặn cả nút chuột phải, chuột giữa và cuộn xuyên nền.

## Tạm biệt vệt trắng

- Sửa lớp mask của blur hiện thành mảng trắng khi ảnh chưa tải, tải thất bại hoặc hiệu ứng blur tắt.
- Sửa vệt trắng trong ô ghi chú của hướng dẫn và trên các ô thư viện.
- Giữ mica trên ảnh đã tải và các cửa sổ, cùng quán tính cuộn hiện có.

## Cửa sổ mở ổn định hơn

Sửa lỗi bộ lọc kéo thả mod nhận sự kiện trong lúc cửa sổ đang được thu hồi, có thể làm các màn hình skin, tạo bản chơi, xác nhận xóa hoặc trang chủ lỗi khi mở. Kéo thả mod vẫn hỏi bản chơi đích trước khi cài.

## Các ô nằm đúng chỗ

- Sửa lưới thư viện, bản chơi và cosmetic tự xuống dòng sớm, bỏ trống cả một cột.
- Mô tả trong ô thư viện gọn hơn ở cửa sổ quản lý bản chơi, tránh chồng nút cài đặt.
- Bộ lọc và nội dung hướng dẫn chuyển bố cục theo chiều rộng cửa sổ và cỡ chữ, dễ đọc trên màn hình nhỏ hoặc khi tăng tỉ lệ giao diện.

## Kiểm tra trước khi phát hành

Đã kiểm tra giao diện Tiếng Việt / English ở nhiều kích thước và tỉ lệ 100%, 125%, 150%; kiểm tra ảnh đang chờ, tải thành công và tải thất bại. Các bài kiểm tra hồi quy chạy cả Qt offscreen và OpenGL thực. Quy trình phát hành chạy bộ kiểm tra mã nguồn và chạy thử gói đóng sẵn trên cả bốn nền tảng.

## Tải và cập nhật

- **Windows x64:** bộ cài `setup.exe` và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

Launcher tiếp tục thông báo bản mới; Windows và Linux tải/cài khi bạn chọn cập nhật, macOS mở trang tải. Gói được kiểm SHA-256 trước khi áp dụng. Google và Premium dùng dịch vụ thật; bản phát hành không mở Ultimate TEST. File đính kèm gồm bộ cài, gói portable/cập nhật và `SHA256SUMS`.
