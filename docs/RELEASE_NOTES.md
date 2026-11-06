# Nostalgia Launcher 1.2.8

Sửa lỗi tạo bản chơi Horizon (Rust) trên Windows khi giải nén một file có đường dẫn dài hơn giới hạn Win32, ví dụ ember_fields.json trong tools/fixtures/biome_datapacks.

- Giải nén và dọn file tạm dùng đường dẫn mở rộng của Windows, hoạt động khi LongPathsEnabled chưa bật.
- Giữ toàn bộ build đã xác minh chữ ký và SHA-256; không bỏ fixtures, exporter hoặc tắt kiểm tra an toàn archive.
- Giữ nguyên cấu hình và world. Sau khi cập nhật, thử tạo bản Horizon lại; archive đúng hash đã tải được dùng lại.
- Bổ sung kiểm thử giải nén, công bố và dọn build trên Windows thật với giới hạn MAX_PATH đang bật trong máy CI.

Bản này giữ các sửa lỗi 1.2.7: manifest Mojang đúng hash của Horizon và hộp thoại thống kê cho người nâng cấp. Lựa chọn từ chối hoặc xác nhận trong 1.2.7 tiếp tục được giữ qua cập nhật 1.2.8.

Xem [Horizon và giới hạn tương thích](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.8/docs/HORIZON.md) và [quyền riêng tư](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.8/docs/PRIVACY.md).

Có gói Windows x64, Linux x64, macOS Intel và Apple Silicon, kèm SHA256SUMS. Kiểm tra cập nhật trong Cài đặt; macOS mở trang tải để cài thủ công.
