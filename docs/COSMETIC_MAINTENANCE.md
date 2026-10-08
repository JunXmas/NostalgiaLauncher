# Bảo trì và phát hành cosmetic

Danh mục gốc: [`src/nostalgia/social/cosmetics.json`](../src/nostalgia/social/cosmetics.json).
Launcher đọc danh mục khi khởi động. Picker, avatar, banner và đường lưu không còn liệt kê
cố định ba mã cosmetic. Đây là quy trình cập nhật theo phiên bản; không có tải mã QML hoặc
ảnh từ URL tuỳ ý, và chưa có trang quản trị trực tuyến.

## Thêm một bộ

1. Đặt hai ảnh PNG trong `src/nostalgia/ui/qml/assets/cosmetics/`: `<artwork>-frame.png`
   và `<artwork>-banner.png`. Frame vuông, RGBA, phần giữa để lộ avatar; banner tỷ lệ 3:1.
   Giới hạn file 8 MiB và mỗi chiều 4096 px. Renderer vẫn giải mã frame tối đa 384 px,
   banner 1536 px; tải bất đồng bộ, dùng cache, không chạy animation vô hạn.
2. Thêm một phần tử vào `items`, rồi tăng `revision`. Ví dụ:

   ```json
   {"key":"moonlight","name":"Moonlight","artwork":"moonlight","tint":"#95b8d8","accent":"amethyst","description":"Ánh trăng dịu","state":"active"}
   ```

   `key` là mã lưu trên dịch vụ: không đổi hoặc tái sử dụng mã đã phát hành. `artwork` là
   tiền tố ảnh, không phải đường dẫn hay URL. `accent` chọn một trong ba màu huy hiệu cũ
   (`amethyst`, `emerald`, `amber`); màu của cosmetic dùng `tint` độc lập.
3. Chạy kiểm tra và đồng bộ định nghĩa sang checkout backend:

   ```bash
   uv run python bench/cosmetic_sync.py --backend /duong/dan/nostalgia-backend
   uv run python bench/cosmetic_sync.py --check --backend /duong/dan/nostalgia-backend
   uv run pytest tests/social/test_cosmetic.py tests/ui/test_cosmetic_maintenance.py tests/ui/test_profile_cosmetics.py -q
   ```

   Lệnh chỉ tạo `account-service/src/cosmetic-definition.js`, không deploy, cấp Plus hoặc
   sửa dữ liệu người chơi. CI launcher kiểm tra danh mục và ảnh. Commit cả ảnh/danh mục
   launcher và file sinh của backend để đối chiếu và rollback.
4. Kiểm tra backend bằng `npm test` trong `multiplayer-relay`. Quyền Plus, phiên Google và
   kiểm tra tại thời điểm ghi vẫn chạy trên máy chủ. Sửa danh mục ở máy khách không cấp
   quyền dùng bộ mới hay bộ đã vô hiệu hoá.

## Ngừng cho chọn hoặc gỡ

| `state` | Trong thư viện chọn | Hồ sơ đang dùng | Lưu hồ sơ |
| --- | --- | --- | --- |
| `active` | Có, cho xem thử | Hiển thị | Cần Plus để áp dụng |
| `retired` | Ẩn | Giữ nguyên hình và mã | Chỉ giữ bộ đang dùng; không chọn lại sau khi đổi |
| `disabled` | Ẩn | Hiển thị mặc định | Không cho áp dụng; người chơi có thể bỏ trang trí |

Ưu tiên `retired` khi ngừng phát hành và giữ ảnh để không phá hồ sơ cũ. Dùng `disabled`
khi cần thu hồi bộ; có thể gỡ ảnh của bộ này. Giữ bản ghi mã như một dấu ngừng sử dụng,
không dùng mã đó cho một bộ khác. Không xoá tài khoản, giới thiệu, skin hoặc modpack.
Backend kiểm tra lại bộ `retired` trong câu lệnh ghi, để không phục hồi nhầm sau một lần
đổi đồng thời. Máy khách mới nhận mã cosmetic chưa có ảnh sẽ hiển thị mặc định, không
đọc file từ mã và không làm hỏng toàn bộ hồ sơ/bạn bè.

## Thứ tự ra mắt

Phát hành bản hỗ trợ danh mục/mã tương lai này trước khi mở mã mới cho người chơi:
rc8 cũ chỉ nhận ba mã ban đầu. Sau đó có thể cập nhật backend và launcher có ảnh mới
trong cùng đợt; máy khách đã có cơ chế fallback vẫn đọc được hồ sơ trong lúc cập nhật.
Đổi `revision` không tự deploy dịch vụ hoặc cập nhật ứng dụng đang mở: launcher cần
bản cập nhật và khởi động lại, backend cần triển khai bản đã duyệt. Rollback bằng commit
cũ của danh mục và backend; các bản ghi người chơi vẫn giữ mã của mình.

Đợt này giữ nguyên ba bộ hiện có, không thay giá/gói và không tạo bộ cài hoặc release.
