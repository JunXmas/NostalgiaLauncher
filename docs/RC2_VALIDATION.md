# Kiểm chứng draft Nostalgia 1.2.0rc2

Ngày 2026-10-06 UTC. Client `15d21c4278d06739cfdff5ce8db45d62c67c013a`, nhánh
`preview/glass-review`. Backend private `808e915873fae69341cc4e57e2220f0a720a74e6`,
nhánh `preview/google-plus-rc2`. Chưa deploy backend hoặc nhận tiền thật.

## Kết quả local

- `pytest -m "not network"`: **1377 passed, 7 skipped, 1 deselected**.
  Bao gồm HTTPS cục bộ, Qt, mod metadata, thanh toán, session, multiplayer và kiến trúc.
- Ruff check/format, mypy (459 source files), lockfile và diff whitespace qua.
- Node/Miniflare/workerd/D1/R2: **20 passed**, Google/payOS giả ở biên mạng.
  RSA/HMAC, DB và quyền/thu hồi được thực thi thật trong môi trường test.
- Qt OpenGL (Mesa): **19 passed** ở các trang preview, social, payment và runtime release.
- Ba ảnh Qt OpenGL: **0 cảnh báo QML**, 1440×900 và 1024×600/chữ 150%.
  Hồ sơ Plus trong ảnh dùng dữ liệu mẫu; bộ JAR kiểm mod tự tạo. Không phải giao dịch thật.
- Runtime release nạp giao diện và thoát bằng smoke mode với dữ liệu mới tách riêng.

## Quy trình build

GitHub Actions run: https://github.com/JunXmas/NostalgiaLauncher/actions/runs/37496000815
Workflow kiểm toàn kho trước khi PyInstaller build Windows x64, Linux x64,
macOS arm64 và macOS x64; từng gói phải smoke-test qua trước tạo bộ cài.
Release được tạo DRAFT, không publish và không đưa vào auto-update ổn định.
SHA256SUMS của bộ cài do workflow tạo; ảnh/hướng dẫn bổ sung có manifest checksum riêng.

## Chưa kiểm chứng

Chưa đăng nhập Google/payOS production, chưa chuyển tiền thật, chưa thử Minecraft
modpack/LAN trên nhiều máy hoặc kho keyring thật trên Windows/macOS.
Smoke-test không thay thế thử cài và chơi game trên máy của chủ dự án.

Checker dựa vào metadata và planner có phạm vi hỗ trợ giới hạn; xem DRAFT_TEST_GUIDE.md.
Mỗi thao tác Plus dùng quyền server, không tin checkbox local. Không hứa chống can thiệp
hoặc sao chép bearer/modpack tuyệt đối trên máy của người dùng.
