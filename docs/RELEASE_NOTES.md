# Nostalgia 1.2.0rc19 — Cuộn nhẹ hơn, chơi chung liền mạch hơn

Thư viện lớn vẫn cần dễ khám phá, bạn bè cần nhắn được ngay, và một bản NeoForge đã cài đúng cần chia sẻ được. rc19 tập trung vào những thao tác đó, cùng giao diện Tiếng Việt và English đầy đủ hơn.

## NeoForge: mở phòng với bản chơi hiện có

Sửa lỗi **“Không tìm thấy phiên bản loader. Hãy cài lại loader trước khi chia sẻ”** khi mở phòng với NeoForge. Launcher đọc phiên bản từ metadata khởi động chính thức, không nhầm số hiệu FML với NeoForge.

- Áp dụng cho chia sẻ/đồng bộ modpack, xuất modpack và kiểm tra mod.
- Không cần cài lại loader chỉ để khắc phục lỗi nhận diện này.
- Nhận đúng nhánh NeoForge của Minecraft 26.x khi cài cho máy khách.
- Kiểm tra hồi quy bằng metadata từ installer chính thức cho Minecraft 1.21.1, 1.21.11 và 26.2.

## Danh sách dài, ít gánh nặng hơn

Launcher chỉ dựng các ô gần màn hình và tái sử dụng chúng khi cuộn, thay vì giữ mọi ô cùng lúc. Áp dụng cho thư viện mod, modpack, resourcepack, shader, bản chơi, nội dung đã cài, server, sửa mod, bạn bè, chat, cosmetic và đồng bộ.

- Giữ hiệu ứng mica và quán tính cuộn; giảm kích thước ảnh blur và capture nền không cần thiết.
- Bật/tắt mod giữ vị trí cuộn; trạng thái xác nhận gỡ không chuyển nhầm sang mod khác khi ô được tái sử dụng.
- Kiểm tra cuộn tới đầu/cuối với danh sách 2.000 mục. Hiệu năng thực tế phụ thuộc máy và driver đồ họa.

## Bạn bè: gửi lời chào ngay

Sau khi kết bạn thành công, người chơi có thể gửi tin nhắn ngay, kể cả khi bạn mình ngoại tuyến. Làm mới tài khoản ở nền không khóa nút **Gửi**. Bản nháp được giữ nếu gửi thất bại; người bị chặn hoặc yêu cầu kết bạn chưa được chấp nhận vẫn không thể nhắn.

## Tiếng Việt / English

Hoàn thiện bản dịch cho trang chính, thư viện, bản chơi, tài khoản/skin/cape, bạn bè, server, cosmetic, Premium, cập nhật và hướng dẫn.

Chọn ngôn ngữ trên màn hình đăng nhập hoặc trong **Cài đặt**; giao diện và cửa sổ đang mở đổi ngay, lựa chọn được lưu cho lần sau. Tên người chơi, đường dẫn và log game giữ nguyên; tiền thanh toán vẫn dùng VND.

## Dành cho chủ launcher

Trang quản trị riêng có mục **Số liệu launcher**: hoạt động tài khoản Google theo ngày/tuần/tháng, phiên đang trực tuyến và lượt tải GitHub theo nền tảng/bản phát hành. Số liệu hoạt động tính theo giờ Việt Nam, bắt đầu từ khi triển khai bộ thu thập; lượt tải không phải số người cài duy nhất. Bộ thu thập gặp lỗi không chặn đăng nhập hoặc chat.

## Tải và cập nhật

- **Windows x64:** bộ cài `setup.exe` và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

Launcher tiếp tục thông báo bản mới và chỉ tải/cài khi bạn chọn cập nhật. Gói được kiểm SHA-256 trước khi áp dụng. Google và Premium dùng dịch vụ thật; bản phát hành không mở Ultimate TEST. File đính kèm chỉ gồm bộ cài, gói portable/cập nhật và `SHA256SUMS`.
