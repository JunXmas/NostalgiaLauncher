# Kiểm chứng draft Nostalgia 1.2.0rc5

Ngày 2026-10-06 UTC. Mã bộ cài: `30fcb634980c60128750026959e2522b5bca838d`,
nhánh client `preview/glass-review`. Backend private không đổi:
`808e915873fae69341cc4e57e2220f0a720a74e6`, nhánh `preview/google-plus-rc2`.
Chưa deploy backend hoặc nhận tiền thật.

## Kết quả local

- `pytest -m "not network"`: **1382 passed, 7 skipped, 1 deselected** (244,54 giây).
  Cùng mã nguồn đã qua bước check của workflow release trên GitHub.
- Ruff check/format, mypy (461 source files), lockfile và diff whitespace qua.
- Qt OpenGL (Mesa/Xorg): **44 passed**. Bao gồm lưu tên/RAM vào dữ liệu thật,
  quản lý file mod, block hover/focus, cuộn/giảm chuyển động, popup dự án cho cả
  bốn loại nội dung, thanh toán/QR, font tiếng Việt và runtime release.
- Mười hai ảnh Qt OpenGL: **0 cảnh báo QML**, 1440×900 và 1024×600/chữ 150%.
  Bộ JAR thử tự tạo; ảnh có nhãn DỮ LIỆU MẪU, không phải phiên chơi thật.
- GIF Qt thật: **69 frame**, **0 cảnh báo QML**, thể hiện block xoay, chuyển trang,
  mở/đóng quản lý bản chơi và cuộn đảo hướng. Thời gian GIF đã cố định 15 fps
  để xem trước, không dùng GIF để đo độ trễ của launcher.
- Node/Miniflare/workerd/D1/R2: **20 passed** từ lần kiểm backend ở rc2;
  backend không đổi trong rc5. Google/payOS giả ở biên mạng, RSA/HMAC/DB/quyền
  được thực thi thật trong test.

## Đóng gói

Workflow: https://github.com/JunXmas/NostalgiaLauncher/actions/runs/37504998299
Kiểm toàn kho trước khi build Windows x64, Linux x64, macOS arm64 và macOS x64.
Từng executable phải smoke-test qua trước tạo bộ cài. Release là DRAFT,
không publish và không đưa vào auto-update ổn định.

Cả bốn job build và job release đã thành công. Tải chính tar.gz Linux từ draft,
đối chiếu SHA256SUMS và chạy executable với Qt OpenGL trên Xorg/Mesa: exit 0,
`smoke ok`, không cần LD_PRELOAD. Bộ cài không đóng gói libstdc++.so, tránh
xung đột với Mesa của máy chạy. Đây là kiểm khởi động, chưa phải phiên chơi game.

SHA256SUMS của bộ cài do workflow tạo. PREVIEW_SHA256SUMS riêng cho ảnh/GIF và
hướng dẫn; không thay checksum của bộ cài khi đính kèm tài liệu.

## Giới hạn

Chưa kiểm Minecraft/Forge/modpack/LAN nhiều máy ở vòng UI này. Chưa thử cài trên
Windows/macOS của người dùng, keyring production, đăng nhập Google hoặc trả tiền
thật. Smoke-test không thay thế cài và chơi game trên từng hệ điều hành.

Cuộn tham khảo Lenis của Skew; chưa đo trên màn 120/144 Hz hoặc mọi trackpad.
Xem UI_MOTION_REVIEW.md để biết phạm vi animation và các danh sách còn dùng Qt.
Checker/planner có phạm vi giới hạn; quyền Plus kiểm ở server. Không hứa chống
can thiệp/sao chép bearer/modpack tuyệt đối trên máy người dùng.
