## 1.2.0rc3 — sửa đóng gói OpenGL Linux

- Dùng libstdc++ của hệ điều hành trên Linux để tương thích với driver Mesa mới.
- Giữ các tính năng giao diện, Google/bạn bè, Plus/payOS và kiểm/sửa mod của rc2.
- Draft để thử; dịch vụ Google/payOS vẫn cần cấu hình staging.

## 1.2.0rc2 — Google, bạn bè và Plus draft

- Dùng giao diện mới mặc định, giữ màu cũ và mica; thu gọn bạn bè/chat/chơi chung.
- Tài khoản Google độc lập Minecraft, lời mời qua bạn bè, một phiên dịch vụ hoạt động.
- Bốn gói Plus 29k / 69k / 109k / mua đứt 209k, huy hiệu/màu hồ sơ và kênh preview.
- Luồng payOS xác nhận server, QR nội bộ và khôi phục đơn chờ; client không tự cấp Plus.
- Free kiểm metadata mod; Plus xem phương án hỗ trợ, sao lưu, kiểm hash và hoàn tác.
- Đồng bộ modpack cho khách Free khi được host Plus mời.

**DRAFT để thử, chưa publish.** Google/payOS và các quyền online cần dịch vụ staging
được cấu hình; lượt này chưa deploy backend hay xác minh giao dịch thật.

Xem `DRAFT_TEST_GUIDE.md` đi kèm release để biết cách thử và giới hạn.

## 1.2.0rc1 — UX preview

Bản thử để chủ dự án duyệt trước khi gộp vào nhánh ổn định.

- Trang chủ hướng dẫn bước bắt đầu; thanh bên cuộn và chữ/nút rõ hơn.
- Tùy chọn cỡ chữ, mật độ, ảnh nền, giảm chuyển động, Việt/Anh.
- Tìm/nhóm/ghim bản chơi; sao lưu ZIP, khôi phục sang bản mới, thùng rác.
- Lỗi giữ lại với thử lại và sao chép chi tiết; bàn phím và focus cho điều khiển chính.
- Giữ hai bản vá v1.1.8 và model beacon/bookshelf Minecraft nguyên bản.

Xem [hướng dẫn và giới hạn preview](https://github.com/JunXmas/NostalgiaLauncher/blob/preview/ux-1.2/docs/PREVIEW_REVIEW.md).

# Nostalgia Launcher 1.1.8

## Sửa Forge và modpack

- Sửa lỗi "không có bản loader '47.4.23'" khi modpack dùng số phiên bản Forge ngắn.
- Chọn đúng version ID do installer trả về, kể cả khi đã có loader khác trong máy.
- Sửa trường hợp cài lại Forge/NeoForge đã có; đọc version ID từ metadata installer.

## Icon Minecraft nguyên bản

- Beacon ở Ủng hộ và kệ sách ở Thư viện dùng model JSON và texture PNG nguyên bản từ client Minecraft Java 1.20.1.
- Beacon có lớp kính, lõi và đế obsidian đúng model. Kệ sách dùng mặt trên gỗ sồi và mặt bên sách.
- Tự thay cache icon cũ. Ghi nguồn, quyền sở hữu và hash asset trong gói.
- Sửa vòng lặp QML khi xóa/thay đổi bộ lọc.

## Kiểm chứng

Hai PR đã đạt CI Python 3.12/3.13 và test updater Windows. Đã thử luồng UI Forge/modpack bằng fixture cục bộ, dựng và chạy bản Linux. Quy trình release dựng và smoke-test từng gói Windows, Linux, macOS, kèm SHA256SUMS.

Chưa kiểm chứng khởi động Minecraft bằng installer Forge thật trên máy Windows. Các cải thiện UX tiếp theo sẽ được đưa vào bản preview riêng để duyệt.
