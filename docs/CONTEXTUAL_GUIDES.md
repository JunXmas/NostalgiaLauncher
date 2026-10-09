# Hướng dẫn thao tác trong launcher

Mã trên nhánh `fix/account-menu-visibility`; chưa có trong bộ cài rc13.

## Người chơi

- Ô gợi ý tại trang chủ, bản chơi, bạn bè và cosmetic; nút **Cách dùng** ở thư viện,
  skin, cài đặt, nhật ký và các cửa sổ thao tác.
- Phím **F1** mở hướng dẫn cho trang đang xem. Không tự bật tour hoặc thực hiện tác vụ.
- 17 chủ đề: tài khoản, tạo bản chơi, thư viện, kéo thả mod, skin/cape, bạn bè, host, nhận pack,
  server, plugin, sao lưu, nhập, sửa log, premium, cosmetic, giao diện và nhật ký.
- Popup mica có GIF, các bước đánh số, lưu ý và tìm kiếm có/không dấu.
- Mở trợ giúp trên một popup giữ nguyên biểu mẫu; đóng hướng dẫn trả focus về nút mở.

## Media và hiệu năng

17 GIF được quay từ Qt launcher bằng fixture cục bộ, có nhãn dữ liệu mẫu; không có
cookie, token, mật khẩu, QR đơn thật hay giao dịch thật. Khung viền đánh dấu nút cần
dùng; caption thể hiện từng bước. Skin/cape trong ảnh chỉ phục vụ minh họa.

GIF có khung 720×500, nhịp 8 fps, vòng lặp khoảng 4–5 giây. Bảng màu 96 màu,
toàn bộ khoảng 2,1 MiB. Không gọi dịch vụ media bên ngoài. Thư mục
`src/nostalgia/ui/qml/assets/guides/` đi cùng toàn bộ QML trong wheel/bộ cài.

Chỉ nạp GIF của chủ đề đang mở. `AnimatedImage.cache: false` tránh lưu tất cả frame
trong RAM. GIF dừng khi tạm dừng, giảm chuyển động, ẩn cửa sổ hoặc ứng dụng mất
trạng thái hoạt động; đóng popup bỏ source. Văn bản vẫn dùng được khi GIF lỗi.

## Bảo trì

1. Cập nhật nội dung và ánh xạ clip trong `preview/GuideCatalog.js` khi luồng đổi.
2. Quay lại giao diện bằng dữ liệu fixture: lựa chọn/toggle để mô tả thao tác,
   không chạy đăng nhập, upload, giao dịch hoặc game thật.
3. Chụp các frame theo bước, đánh dấu nút và thêm caption; xuất bằng FFmpeg:
   `palettegen=max_colors=96:stats_mode=diff` rồi
   `paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`, 8 fps, loop 0.
4. Giữ mỗi clip dưới 512 KiB, toàn bộ dưới 5 MiB; xem lại GIF và nội dung cạnh nhau.
5. Chạy `tests/ui/test_guides.py` trên Qt/OpenGL thật: đăng nhập/F1, popup lồng,
   trả focus, pause/ẩn/giảm chuyển động, tìm kiếm, cỡ nhỏ và decode media offline.

Các điểm cần giữ chính xác: Google khác tài khoản Minecraft; chọn skin chưa áp dụng;
cape Microsoft phải sở hữu; nhận pack có rủi ro mã thực thi; server không kèm VPS;
Đã chuyển khoản không tự cấp quyền; sửa mod cần bằng chứng log; cosmetic hồ sơ
không tự hiện trong Minecraft.

## Kéo thả mod từ máy

Thả một hoặc nhiều file `.jar` vào bất kỳ trang hoặc popup nào để chọn bản chơi.
Không chọn sẵn, không cài ngay khi thả; chỉ chép sau khi xác nhận. Các file khác bị
bỏ qua; nhập `.mrpack`/`.zip` ở trang bản chơi vẫn giữ luồng cũ. Nguồn gốc không bị
di chuyển, tải lên hoặc chạy. Đóng Minecraft và đợi tác vụ cài đặt khác trước khi cài.

Mặc định bỏ qua file trùng tên. Nếu bật thay thế, bản cũ nằm trong
`.nostalgia/local-mod-backups/<mã>/` của bản chơi; mod đang tắt vẫn giữ trạng thái
tắt. Cả lô được kiểm tra trước khi ghi; lỗi trong lúc ghi hoàn tác phần đã chép.
Thông tin dự án/phiên bản cũ trong sổ nội dung được bỏ khi thay bằng JAR cục bộ,
để danh sách đã cài đọc lại metadata thay vì hiển thị nhầm phiên bản cũ.

Luồng này không tự giải phụ thuộc hoặc kiểm chứng tương thích của JAR. UI nhắc
nguồn tin tưởng, phiên bản Minecraft và loader trước khi cài.
