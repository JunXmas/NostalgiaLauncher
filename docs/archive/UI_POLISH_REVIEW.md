# Đợt hoàn thiện UI sau rc8

## Thay đổi

- Sửa quán tính: cuộn ngược dùng vị trí đang nhìn thấy thay vì đích cũ phía dưới. Áp dụng cùng bộ điều khiển cho trang và danh sách chọn phiên bản.
- Tạo bản chơi dùng form gọn, danh sách phiên bản có tìm kiếm và giới hạn chiều cao. Giữ lựa chọn khi danh mục cập nhật, kiểm tra chỉ số trước khi chọn và giữ đường cài loader hiện có.
- Thư viện cosmetic riêng: xem thử độc lập với lưu, một bộ đang dùng, đọc hồ sơ mới nhất trước khi lưu để giữ giới thiệu, skin và modpack. Xoá trạng thái khi đăng xuất/đổi tài khoản; quyền áp dụng vẫn được dịch vụ xác nhận.
- Logo Google/Microsoft trên các nút đăng nhập; avatar mở hồ sơ bằng chuột/bàn phím, menu tài khoản có đăng xuất cần xác nhận.
- Bạn bè/Chơi chung thành hai tab; thu gọn phần tài khoản và nội dung trên màn hình nhỏ.
- Trang tài khoản/skin mới giữ các thao tác Microsoft, Ely.by, skin/cape; skin 3D dùng renderer/cache hiện có. Nút dùng skin luôn nhìn thấy trong theme mới.
- Yêu thích có phản hồi và màu rõ hơn. Sửa thứ tự xoá cache trước khi phát thông báo để UI hiển thị ngay trạng thái vừa lưu.
- Thư viện plugin tự tìm nội dung tương thích lần đầu mở tab và khi đổi nguồn/server; giữ kết quả khi chuyển tab. Thẻ có avatar, nền ảnh mờ, hỗ trợ icon Hangar. Nút xoá server xuất hiện trong danh sách và chân hộp thoại, vẫn chuyển thế giới vào thùng rác để lấy lại.
- Tab chuyển động hữu hạn; hiệu ứng kính theo đúng vị trí sau chuyển trang. Giảm chuyển động vẫn được tôn trọng.

## Kiểm tra

- Qt: cuộn ngược liên tục trước khi chạm đích, tìm/chọn bản đầu tiên, chọn đúng game/loader và tạo bản chơi thật qua façade.
- Cosmetic: tài khoản free chỉ xem thử; Plus lưu một bộ và giữ các trường hồ sơ mới sửa; đăng xuất không xoá tài khoản Minecraft.
- Tương tác chuột thật với avatar; đăng xuất qua xác nhận; yêu thích lưu và cập nhật UI ngay.
- Server: tự tải thư viện, đổi nguồn, cài file JAR qua đường cài thật, xoá/hủy xoá và giữ world trong `.trash`.
- Giao diện: Qt/OpenGL ở 1440×900, 1024×600 và cỡ chữ 150%; ảnh chụp thực tế, kiểm tra cảnh báo QML.
- Ruff, mypy và bộ pytest không chạm mạng.

Ảnh preview để riêng trong `/workspace/artifacts/nostalgia-ui-polish`, không nằm trong release assets. Các ảnh dùng tài khoản/bạn bè/danh mục kiểm thử để minh hoạ UI; không chứng minh Google/backend production đã được triển khai. Chưa tạo bộ cài hoặc release mới cho đợt thay đổi này.

### Kết quả chốt

- Chạy riêng hai nhóm để kiểm tra UI và nghiệp vụ: `tests/ui` đạt **335 passed, 1 skipped**; phần còn lại đạt **1165 passed, 6 skipped, 1 deselected**. Tổng cộng **1500 bài đạt**. Các bài cần mạng không chạy.
- Chạy thêm trên Qt/OpenGL thực tế: **13 passed**, gồm quán tính chọn phiên bản, cosmetic, thao tác avatar/đăng xuất, plugin và xác nhận xoá server.
- Ruff đạt; 589 file đúng định dạng; mypy đạt trên 545 file nguồn/kiểm thử; `git diff --check` sạch.
- 12 ảnh preview; cả ba nhật ký cảnh báo QML khi chụp đều rỗng. Môi trường OpenGL dùng llvmpipe, nên đợt này không đưa ra cam kết FPS trên GPU người dùng.
- Bộ cài draft rc8 giữ nguyên. Các thay đổi này chỉ nằm trên nhánh `preview/glass-review`; không triển khai backend hoặc tạo release mới.
