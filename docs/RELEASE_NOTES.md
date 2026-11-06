# Nostalgia Launcher 1.2.5

Bản cập nhật này bổ sung khả năng tạo bản chơi **Horizon (Rust)** ở trạng thái thử nghiệm và kích hoạt **thống kê sử dụng tự nguyện** nhằm định hướng cải thiện launcher.

## Horizon (Rust) — thử nghiệm

- Trong **Tạo bản chơi**, có thể chọn **Horizon (Rust)** cho Minecraft **26.3**.
- Hỗ trợ hồ sơ offline. Với Ely.by, launcher dùng tên offline và skin/cape cục bộ; **không chuyển token Ely.by** sang Horizon và **chưa hỗ trợ đăng nhập server online-mode bằng Ely.by/offline**.
- Hồ sơ Microsoft hiện có sử dụng luồng làm mới phiên; token không được đưa vào tham số dòng lệnh.
- Tải bản Nightly chính thức, xác minh chữ ký Ed25519 và SHA-256 trước khi cài; các lần chơi sau tái sử dụng tài nguyên đã chuẩn bị khi có thể.
- Dữ liệu, bản chơi và thế giới Horizon được tách riêng với Minecraft Java và Nos Client. **Không tự chuyển world cũ** sang Horizon.
- Tắt telemetry, heartbeat, Discord presence và cosmetic presence riêng của Horizon trong đường chạy qua Nostalgia.

**Lưu ý:** Horizon đang thử nghiệm; mod Java, Fabric/Forge, Iris, Nos Client và đồng bộ mod của phòng chơi Nostalgia **không tương thích** với bản chơi Horizon. Minecraft cần được sở hữu hợp lệ. Xem [hướng dẫn Horizon](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.5/docs/HORIZON.md).

## Giúp cải thiện Nostalgia — chỉ khi đồng ý

- Dịch vụ thống kê tùy chọn đã được triển khai; có thể chọn tham gia mà **không cần đăng nhập Google**.
- Tùy chọn mặc định **không gửi dữ liệu**. Launcher hỏi một lần khi phù hợp, không chọn sẵn đồng ý. Người chơi có thể từ chối hoặc thay đổi quyết định trong **Cài đặt → Giúp cải thiện Nostalgia**.
- Nếu đồng ý, launcher chỉ gửi một tín hiệu **bản cài tham gia hoạt động/ngày UTC**, kèm phiên bản launcher và nhóm hệ điều hành. Đây **không phải** số người dùng duy nhất hoặc số giờ chơi.
- **Không thu thập sự kiện khởi chạy Minecraft**, lịch sử game/world, danh sách mod, tài khoản, token, HWID hoặc báo cáo lỗi. Từ chối không hạn chế tính năng.
- Dữ liệu tổng hợp được dùng để ưu tiên kiểm thử, sửa lỗi theo phiên bản/hệ điều hành và định hướng phiên bản tiếp theo; không tự suy ra bản nào có lỗi.
- Luồng thống kê mới không dùng IP làm mã định danh. Tuy nhiên các nhà cung cấp hạ tầng vẫn có thể xử lý IP/log kết nối; không cam kết ẩn danh tuyệt đối. Xem [chính sách và giới hạn đã công khai](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.5/docs/PRIVACY.md).

## Cài đặt và cập nhật

Hỗ trợ các gói launcher cho **Windows x64**, **Linux x64**, **macOS Apple Silicon (arm64)** và **macOS Intel (x64)**. Các gói phát hành kèm file **SHA256SUMS** để xác minh tải về.

Có thể kiểm tra cập nhật trong **Cài đặt → Cập nhật**. Bản cập nhật dành cho macOS mở trang tải để cài thủ công.

Các bản chơi Minecraft Java, hồ sơ cũ và chức năng Nos Client vẫn được giữ riêng và tiếp tục hoạt động như trước.
