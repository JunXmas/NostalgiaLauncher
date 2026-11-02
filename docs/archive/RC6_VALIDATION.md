# Kiểm chứng draft Nostalgia 1.2.0rc6

Ngày 2026-10-07 UTC. Tag bộ cài `v1.2.0rc6`, nhánh client `preview/glass-review`.
Backend private không đổi: `808e915873fae69341cc4e57e2220f0a720a74e6`,
nhánh `preview/google-plus-rc2`. Chưa deploy backend hoặc nhận tiền thật.

## Kết quả local

- `pytest -m "not network"`: **1394 passed, 7 skipped, 1 deselected**, 254,79 giây.
- Ruff check/format (496 file), mypy (468 source file), lockfile và diff whitespace qua.
- Qt OpenGL trên Xorg/Mesa: **56 passed**. Bao gồm skin 3D, Steve/Alex, skin cũ
  64×32 và lớp áo ngoài, kéo/phím xoay, ẩn/hiện, chỉ nạp thẻ trong vùng nhìn,
  mica popup và căn chỉnh backdrop, quản lý bản chơi, block, cuộn, thanh toán,
  font, popup dự án và runtime release.
- Mã upload/xác thực skin trong `skin/`, facade skin và account bridge không đổi.
  Các test Mojang và Ely.by qua: upload byte ảnh, refresh token Microsoft trước
  upload, lỗi 401, áp dụng skin kho vào Ely.by và đồng bộ cache.
  Đây là kiểm thử HTTP fixture, chưa upload bằng tài khoản thật trong phiên này.
- Bảy ảnh Qt OpenGL: **0 cảnh báo QML**, 1440×900 và 1024×600/chữ 150%.
  Tài khoản, skin mẫu và mã Microsoft trong ảnh là dữ liệu preview cục bộ.
- GIF kéo xoay skin: **50 frame Qt thật**, 15 fps để xem trước; không dùng GIF
  để đo tốc độ khung hình hoặc độ trễ của launcher.
- Backend: **20 passed** từ vòng rc2; mã backend không đổi. Google/payOS giả
  ở biên mạng, RSA/HMAC/DB/quyền được thực thi trong test.

## Hiệu năng skin

Preview dùng hình học khối Minecraft, UV và phép chiếu 3D, raster hóa ở worker
rồi QML đọc PNG/atlas. Không thêm QtQuick3D, WebEngine hoặc render timer khi đứng yên.
Skin gốc không bị ghi đè; dữ liệu tạo thêm nằm trong `cache/skin-preview`.

Benchmark local `bench/skin_preview.py`, 5 lần trên môi trường Linux này:

- Median tạo atlas lần đầu: **240,64 ms**, chạy ở worker.
- Median đọc cache atlas có sẵn: **0,156 ms**.
- Atlas 72 góc: 1536×1536, **9 MiB RGBA**; PNG skin mẫu 312.549 byte.
- Cache frame raster giới hạn **4 MiB**; cache mesh 8 mẫu, bảng URL 48 thumbnail
  và 8 atlas; disk cache mục tiêu 64 MiB, giữ các file đang được tham chiếu.

Thẻ kho dùng thumbnail tĩnh. Ảnh ngoài vùng nhìn và atlas của skin khi ẩn/thu nhỏ
được bỏ nguồn QML. Các số trên không đại diện tổng RAM/GPU của launcher hay mọi
máy người dùng; cache file đang dùng có thể khiến disk vượt mục tiêu tạm thời.

## Đóng gói và đối chiếu

Workflow release chạy check toàn kho trước khi build Windows x64, Linux x64,
macOS arm64 và macOS x64. Mỗi executable phải smoke-test qua trước tạo bộ cài.
Release được tạo **DRAFT**, không publish, không phát qua auto-update ổn định.
Kết quả build và lần chạy bộ cài tải về được ghi trong mô tả draft sau khi hoàn tất.

`SHA256SUMS` của bộ cài do workflow tạo. `PREVIEW_SHA256SUMS` riêng cho bảy PNG,
GIF và ba tài liệu; hai manifest không thay thế nhau. Tài liệu và ảnh được đính
kèm ngay khi tạo draft cùng bộ cài.

## Giới hạn

Chưa đăng nhập/upload skin bằng Microsoft/Ely.by thật, OAuth Google hoặc thanh toán
production trong phiên này. Chưa chạy Minecraft/Forge/modpack/LAN nhiều máy ở vòng UI
này, chưa cài trên Windows/macOS của người dùng. Smoke-test chỉ kiểm khởi động.
Xem DRAFT_TEST_GUIDE.md để thử các luồng này trên máy và dịch vụ staging.
