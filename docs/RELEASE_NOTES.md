# Nostalgia 1.2.0rc26 — Mở world, mời bạn, cùng chơi

Chơi chung có luồng rõ ràng hơn: bạn luôn thấy mình đang ở bước nào, cần làm gì tiếp theo và mời ai vào world. Bản này cũng giảm các lần gọi nền để tiết kiệm tài nguyên của dịch vụ tài khoản.

## Mời bạn ngay trong phòng

1. Vào **Bạn bè → Chơi chung → Mở phòng**, chọn bản chơi và bấm **Khởi chạy Minecraft**.
2. Trong world Minecraft, chọn **Esc → Open to LAN → Start LAN World**. Launcher tự nhận cổng LAN.
3. Quay lại launcher, chờ world và modpack sẵn sàng rồi bấm **Mời chơi** cạnh tên bạn trực tuyến.

Mở cửa sổ host tự chuyển sang tab Chơi chung. Bảng phòng hiển thị ba bước, hướng dẫn LAN ở đúng thời điểm và danh sách bạn có thể mời ngay tại đó. Bạn không cần chọn một cuộc chat để gửi lời mời. Phòng đang khóa hoặc nội dung chia sẻ chưa sẵn sàng vẫn được kiểm tra trước khi mời.

Người nhận bấm **Vào phòng**, xem nội dung cần đồng bộ nếu có, rồi kết nối trong Minecraft. Nút **Chép địa chỉ vào Minecraft** nằm ngay trong bảng phòng khi kết nối đã sẵn sàng. Giữ Minecraft và launcher mở trong lúc chơi. Hướng dẫn có GIF bằng **Tiếng Việt / English** đã cập nhật theo luồng mới.

## Ít gọi nền hơn, giữ các thao tác trực tiếp

- Khi không mở chat, danh sách bạn bè làm mới **4 lần/phút thay vì 20 lần/phút** — giảm 80% số lần polling định kỳ ở trạng thái này.
- Khi rời trang bạn bè, launcher giữ tin nhắn đã tải và ngừng yêu cầu tin nhắn ở nền. Mở lại trang sẽ làm mới ngay.
- Chat đang mở cập nhật mỗi **5 giây**; gửi tin, gửi yêu cầu kết bạn và mời chơi vẫn xử lý ngay khi bấm.
- Backend đã giảm ghi trạng thái online trùng lặp. Kiểm tra phiên một máy, chữ ký chống phát lại và quyền Premium vẫn do máy chủ thực hiện.

Đây là giảm số lần gọi nền; mức giảm tổng lượt ghi database phụ thuộc hoạt động thực tế của người dùng.

## Mica và bố cục ổn định hơn

- Sửa callback của ảnh mica gọi vào ô thư viện đã đóng khi chuyển giữa mod, modpack, shader và resourcepack.
- Các bước mở phòng xuống dòng theo chiều rộng; tiêu đề cửa sổ host tự dành đủ chỗ khi tăng cỡ chữ.
- Danh sách bạn trong phòng chỉ dựng các ô gần màn hình, giữ cuộn nhẹ khi có nhiều bạn.

## Tải và cập nhật

- **Windows x64:** bộ cài `setup.exe` và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

Launcher giữ cơ chế cập nhật hiện có: thông báo bản mới, tải và cài khi bạn chọn cập nhật; macOS mở trang tải. Gói được kiểm SHA-256 trước khi áp dụng. Google và Premium dùng dịch vụ thật, không mở Ultimate TEST. File đính kèm chỉ gồm bộ cài, gói portable/cập nhật và `SHA256SUMS`.
