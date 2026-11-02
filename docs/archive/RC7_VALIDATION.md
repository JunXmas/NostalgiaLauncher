# Kiểm chứng draft Nostalgia 1.2.0rc7

Ngày 2026-10-07 UTC. Tag bộ cài `v1.2.0rc7`, nhánh client `preview/glass-review`.
Backend private không đổi: `808e915873fae69341cc4e57e2220f0a720a74e6`.
Chưa deploy backend hoặc nhận tiền thật.

## Phạm vi

- Tự đọc tên/phiên bản JAR của modpack và mod chép tay, không cần bấm nhận diện.
  Metadata Fabric, Quilt, Forge, NeoForge và mcmod.info; Forge có thể lấy phiên bản
  từ manifest khi dùng `${file.jarVersion}`.
- Local scan ở worker có kết quả trước mạng; lookup hash Modrinth bổ sung dự án,
  icon và nhãn Đã cài. CurseForge giữ dự án/phiên bản từ manifest chỉ khi SHA-1
  file sau overrides vẫn khớp. Không đoán ID theo tên file/tên mod.
- Cache mtime/size; JAR giới hạn 512 MiB, metadata giới hạn 256 KiB, cache JSON
  giới hạn 2 MiB khi đọc. Không chạy Java hoặc giải nén toàn bộ JAR ở UI thread.
  Watcher thư mục debounce 160 ms cập nhật thêm/xoá; không có polling lúc rảnh.
- Worker nhận diện riêng không khoá bật/tắt/gỡ. Đổi bản chơi bỏ kết quả cũ;
  file bị thay/xoá trong lúc lookup không được ghi nhận nhầm. Cache yêu cầu âm
  tối đa 32 ngữ cảnh/5 phút tránh gọi lại khi lọc hoặc bật/tắt không đổi nội dung.
- Cuộn nấc chuột, pixel trackpad và kéo–thả dùng controller FrameAnimation chung.
  Đo vận tốc kéo thực tế, kiểm cả trường hợp native flick bị tắt; giữ con trỏ
  đứng yên trước khi thả không tạo đà giả.
  Độ hãm theo duration 1,5 giây của Lenis trong mã Skew đã lưu ngày 2026-10-06;
  lần tải lại tham khảo ngày 2026-10-07 trả HTTP 403 trong môi trường này.
- Kéo scrollbar đặt trực tiếp; Giảm chuyển động bỏ quán tính. Native ListView/GridView
  vẫn giữ virtualization; dropdown nhỏ dùng hành vi Qt thông thường.
- Focus ô phiên bản ở theme mới dùng viền bo góc, bỏ viền trắng hình vuông legacy.
  Thẻ Optimized tự tăng chiều cao và lưới loader đổi số cột theo cỡ chữ, tránh
  chữ đè nút ở 1024×600/chữ 150%.

## Kết quả local

- `pytest -m "not network"`: **1407 passed, 7 skipped, 1 deselected**, 273,83 giây.
- Ruff check/format (504 file), mypy (474 source file), lockfile và diff whitespace qua.
- Qt OpenGL trên Xorg/Mesa: **61 passed**; đã kiểm lại hai test cuộn sau xử lý
  mép danh sách, **2 passed**. Bao gồm kéo–thả khi native flick tắt, giữ trước khi
  thả, Reduced Motion, pixel wheel, focus bo góc, nhận diện tự động/hash/icon/nhãn
  Đã cài, đổi target khi đang quét, watcher, skin 3D, mica, font và runtime release.
- Bốn PNG ở 1440×900/1024×600/chữ 150% và GIF 68 frame: **0 cảnh báo QML**.
- Mã skin/upload/xác thực và facade skin không đổi; test Mojang/Ely.by, refresh
  token và áp dụng skin kho qua bằng HTTP fixture.

Ảnh/GIF là cửa sổ Qt/OpenGL thật, không phải mockup. Tên tài khoản và JAR trong
ảnh là dữ liệu mẫu cục bộ; không đại diện phiên Minecraft hay file mod đã tải thật.
GIF có 68 frame ở 15 fps phục vụ xem chuyển động, không dùng đo FPS launcher.

## Đóng gói

Workflow kiểm toàn kho trước khi build Windows x64, Linux x64, macOS arm64 và x64.
Mỗi executable phải smoke-test qua trước khi tạo bộ cài. Release được tạo DRAFT,
không publish, không phát qua auto-update ổn định. Kết quả CI và lần chạy bộ cài
Linux tải về được ghi trong mô tả draft sau khi hoàn tất.

`SHA256SUMS` đối chiếu 11 bộ cài. `PREVIEW_SHA256SUMS` riêng đối chiếu bốn PNG,
GIF và ba tài liệu; ảnh/tài liệu được đính kèm ngay khi tạo draft cùng bộ cài.

## Giới hạn

Chưa đo 120/144 Hz hoặc thử mọi chuột/trackpad Windows. Mod không có metadata
hỗ trợ vẫn hiện tên file; mod chưa có hash trên Modrinth không được gán ID.
Watcher thư mục theo thông báo của hệ điều hành, không thay thế nút làm mới/
Nhận diện lại khi sửa trực tiếp bên trong file mà hệ điều hành không báo đổi thư mục.

Mã skin/upload/xác thực Microsoft/Ely.by được giữ; HTTP fixture đã kiểm các luồng
này, chưa đăng nhập/upload bằng tài khoản thật ở lượt này. Không chạy Minecraft/
Forge/modpack/LAN nhiều máy, OAuth Google hoặc thanh toán production ở vòng UI này.
Windows/macOS chỉ có CI build/smoke; chưa thử tương tác trên máy người dùng.
Backend không đổi, giữ kết quả 20 test của vòng rc2; chưa deploy production.
