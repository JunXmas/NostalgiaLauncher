## 1.2.0rc7 — Nhận diện modpack và cuộn quán tính

- Tự đọc tên/phiên bản mod từ JAR Fabric, Quilt, Forge, NeoForge và mcmod.info; không cần bấm nhận diện. Hoạt động offline, quét ở nền và cache theo file.
- Đối chiếu hash Modrinth tự bổ sung ID, icon và trạng thái Đã cài; pack CurseForge giữ ID từ manifest khi hash file khớp. Không đoán ID bằng tên file.
- Thêm/xoá mod khi mở danh sách được cập nhật bằng watcher; đổi bản chơi không nhận kết quả cũ. Bật/tắt/gỡ vẫn dùng được trong lúc nhận diện nền.
- Cuộn theo tham số Lenis đã tham khảo trên Skew: làm mượt cả nấc chuột và pixel trackpad, kéo nội dung rồi thả tiếp tục trôi và hãm dần. Danh sách phiên bản/loader, tài khoản, log và thư viện nâng cao dùng chung cơ chế.
- Sửa viền focus trắng hình vuông quanh ô phiên bản đã chọn, giữ viền bo góc và hệ màu hiện có. Thẻ Optimized/lưới loader co giãn để chữ 150% không tràn ở cửa sổ nhỏ.
- Giữ mica, skin 3D và các chức năng của rc6. Release DRAFT để thử, chưa deploy backend Google/payOS production.

## 1.2.0rc6 — Mica xuyên thấu và skin 3D

- Popup thêm tài khoản, mã đăng nhập Microsoft và cài modpack lấy đúng nội dung trang phía sau, bỏ lớp nền đặc; kính không bị lệch khi mở.
- Skin dùng mesh 3D đúng UV Minecraft, Steve/Alex, mũ/áo ngoài và skin 64x32 cũ; kéo/phím để xoay 360°. Thẻ skin trong kho hiện cả nhân vật 3D.
- Một worker dựng ảnh và atlas, cache trên đĩa có giới hạn; xoay chỉ dịch texture đã nạp. Thẻ ngoài vùng nhìn không nạp preview, ẩn/thu nhỏ cửa sổ giải phóng nguồn ảnh; không có timer render lúc đứng yên.
- Kho skin có cuộn quán tính; ảnh dựng không thêm QtQuick3D hoặc thư viện GPU mới vào bộ cài.
- Giữ toàn bộ UI và tính năng của rc5. Draft dành cho thử, chưa deploy Google/payOS production.

## 1.2.0rc5 — Giao diện mới và popup co giãn

- Giữ toàn bộ quản lý bản chơi, Đã cài, bộ lọc, font và chuyển động của giao diện mới ở rc4.
- Thêm tài khoản và cài modpack nhanh dùng khung mica chung, co giãn theo cửa sổ, có cuộn quán tính; nội dung dài và chữ 150% vẫn tới được các nút.
- Hai popup nằm giữa cửa sổ, hỗ trợ Escape; thẻ loại tài khoản và các hàng thao tác tự bố trí theo chiều rộng.
- Các vùng cuộn dùng chung lấy thiết lập cỡ chữ/Giảm chuyển động của launcher cả khi đang ở theme classic.
- Draft để thử; Google/payOS vẫn cần cấu hình dịch vụ staging.

## 1.2.0rc4 — Giao diện nhất quán & chuyển động

- Quản lý bản chơi có Tổng quan, Nội dung đã cài, Hiệu năng, Sao lưu & dữ liệu; thao tác lưu và mở thư mục luôn ở cuối cửa sổ.
- Đã cài và bộ lọc thư viện dùng giao diện mới, không chuyển sang toàn bộ trang thư viện cũ.
- Đồng bộ nút, ô nhập, công tắc, checkbox, slider, thẻ và các cửa sổ tạo/nhập/sao lưu/xác nhận theo hệ màu hiện có.
- Khôi phục block Minecraft gốc xoay khi hover hoặc focus sidebar; chỉ báo trang trượt, nút có nhịp nhấn, trang/popup mờ chuyển nhẹ.
- Tiêu đề Manrope, chữ đọc Inter, đầy đủ tiếng Việt và cỡ chữ theo thiết lập.
- Cuộn bằng nhịp render với độ hãm theo Lenis trên skewclient.store. Home, thư viện, Đã cài, quản lý bản chơi, form và Cài đặt cùng cơ chế; trackpad dùng quán tính hệ điều hành, Giảm chuyển động bỏ hiệu ứng.
- Bộ cài Linux sử dụng libstdc++ của máy để tương thích Mesa mới, tránh xung đột thư viện từ runner build.

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
