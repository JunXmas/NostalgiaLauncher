# Blur thư viện và danh mục cosmetic

## Kết quả

- Thư viện mod, resource pack, modpack, shader và thẻ plugin dùng chung `CardMica`:
  blur nền avatar, bo góc, lớp tối giữ chữ rõ và giữ hệ màu theo trang. Đã cài trong
  theme mới cũng dùng thành phần này.
- Nền giải mã tối đa 320×320; shader capture ở nửa kích thước ô. Nguồn nền được bỏ
  khi ô ngoài viewport hoặc thư viện bị ẩn. Renderer software giữ nền màu nhẹ;
  không thêm animation vô hạn. Không đưa ra cam kết FPS từ máy llvmpipe kiểm thử.
- Kích thước thẻ/grid theo cỡ chữ; phần số tải được elide trước nút cài để không đè
  nhau ở 1024×600 và chữ 150%.
- Cosmetic lấy định nghĩa từ JSON, không liệt kê bộ cố định trong UI hoặc đường lưu.
  Có `active`, `retired`, `disabled`, revision, kiểm tra ảnh và công cụ sinh danh mục
  backend. Giữ mã cũ, hỗ trợ mã tương lai bằng fallback và không đọc file từ mã mạng.
- Backend tiếp tục kiểm tra Plus/phiên/chữ ký, danh mục được duyệt và điều kiện tại
  thời điểm ghi. Một bộ retired chỉ được giữ trên hồ sơ đang dùng; disabled trở về
  mặc định, không xoá hồ sơ. Bỏ cosmetic vẫn được phép cho tài khoản free.

## Kiểm tra

- `tests/ui`: **343 passed, 1 skipped**.
- Nhóm thư viện/cosmetic/server trên Qt/OpenGL thật: **25 passed**, gồm đúng nguồn
  ảnh cho cả bốn loại, giải phóng nền ngoài viewport, thêm bộ qua dữ liệu, fallback
  và bố cục ở cỡ chữ 150%.
- Kiểm tra social, quy ước, kiến trúc và website: **73 passed**; hồi quy cuối về
  cosmetic, popup phiên bản và content bridge: **20 passed**. Các nhóm có trùng bài
  với bộ UI, không cộng chúng thành tổng bài độc lập.
- Backend `npm test` trong multiplayer-relay: **41 passed**; có kiểm quyền đối với
  mã mới, retired/disabled và các quyền Plus hiện có.
- Ruff/format đạt (595 file); mypy đạt (550 file); `git diff --check` sạch. Lệnh
  `cosmetic_sync.py --check --backend ...` xác nhận ảnh và hai danh mục đồng bộ.

## Preview và phát hành

5 ảnh chụp Qt/OpenGL thực tế để riêng ở
`/workspace/artifacts/nostalgia-library-blur`. Các thẻ dùng danh mục công khai được
lưu từ Modrinth, tài khoản ngoại tuyến để minh hoạ. Nhật ký cảnh báo QML rỗng.
Ảnh không nằm trong Git hoặc release assets. Không tạo bộ cài/release mới và không
deploy backend. Hướng dẫn phát hành bộ mới nằm trong `COSMETIC_MAINTENANCE.md`;
cần cập nhật client hỗ trợ fallback trước khi đưa mã mới tới client rc8 cũ.
