# Nostalgia 1.2.0rc20 — Mica sạch hơn, bố cục gọn hơn

rc20 sửa vệt trắng và những khoảng trống bất thường bạn gặp trong thư viện, bản chơi và hướng dẫn. Ảnh chưa tải vẫn có nền tối đồng nhất; ảnh tải xong giữ hiệu ứng mica quen thuộc.

## Tạm biệt vệt trắng

- Sửa lớp mask của blur hiện thành mảng trắng khi ảnh chưa tải, tải thất bại hoặc hiệu ứng blur tắt.
- Sửa vệt trắng trong ô ghi chú của hướng dẫn và trên các ô thư viện.
- Giữ mica trên ảnh đã tải và các cửa sổ, cùng quán tính cuộn hiện có.

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
