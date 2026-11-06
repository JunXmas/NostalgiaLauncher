# Horizon trong Nostalgia Launcher

Horizon là tiến trình Minecraft native Rust độc lập. Trong **Tạo bản chơi**, chọn
**Horizon (Rust)**. Nhánh này hỗ trợ Minecraft 26.3, Launch API 0.1.x; không chuyển các
bản chơi Java/Nos hiện có sang Horizon. Hệ điều hành có gói chính thức gồm Linux x64,
Windows x64/ARM64 và macOS Intel/Apple silicon.

## Tài khoản và skin

- Offline: dùng tên 3–16 ký tự gồm chữ cái, chữ số hoặc gạch dưới qua `--name`; không
  tạo phiên Microsoft giả. Chơi đơn, LAN và server cho phép offline được hỗ trợ bởi engine.
- Microsoft: giữ luồng làm mới tài khoản hiện có; session JSON đi qua stdin, token
  không xuất hiện trong argv hoặc file phiên. Token được che khỏi output của launcher.
- Ely.by: dùng tên ở chế độ offline và texture công khai/cache của chính tài khoản.
  PNG, kiểu tay classic/slim và cape cục bộ được đưa cho Horizon qua biến môi trường.
  Không đưa token Ely.by vào game và không dùng authlib-injector. Chưa triển khai xác
  thực Ely.by cho engine hoặc đồng bộ skin Ely cho người chơi khác; không hứa chơi được
  server online-mode bằng tài khoản offline/Ely.

## Cài và bảo vệ dữ liệu

Launcher tải gói Nightly chính thức, xác minh Ed25519 của `SHA256SUMS` với khóa đã ghim,
rồi đối chiếu SHA-256 trước khi giải nén. Đường dẫn thoát thư mục, symlink, hardlink,
file đặc biệt và gói vượt giới hạn bị từ chối. Build được công bố nguyên thư mục, giữ
exporter và research lock; các lần cài cùng build có khóa liên tiến trình.

Mỗi bản chơi giữ SHA-256 build trong `horizon_build_id`, `runtime_kind=horizon` và mã
phiên bản riêng `horizon-26.3`. Launcher cũ sẽ không tìm thấy phiên bản Java mang mã đó,
thay vì tự mở world Horizon bằng Java. Thư mục game mới phải trống; thế giới hiện có
không được tự chuyển đổi. Build của bản chơi đã tạo không tự đổi theo Nightly mới.

Kho dùng chung `data_dir/horizon/builds/<sha>/` chứa binary và tài nguyên đã chuẩn bị.
Minecraft 26.3, server jar có hash, thư viện/assets và Java 25 được tải vào kho launcher;
Java chỉ dùng để chuẩn bị tài nguyên. Không phân phối lại tài nguyên Mojang trong gói
launcher. Người chơi cần sử dụng bản Minecraft mình sở hữu. Chuẩn bị lần đầu có thể
mất vài phút; các lần chơi dùng lại tài nguyên đã kiểm tra và hoạt động khi mất mạng.
Tác vụ chuẩn bị có thời hạn, hỗ trợ yêu cầu hủy ở API và dừng tiến trình con riêng.

## Giới hạn tương thích

Horizon Nightly còn thử nghiệm. Mod Java, Fabric/Forge, Iris và Nos Client không chạy
trong tiến trình này. Quản lý nội dung native trong game hoặc thư mục bản chơi; công
cụ cài/sửa mod Java và xuất modpack Java được chặn. Sao lưu dữ liệu bản chơi vẫn dùng
được. Chơi chung Nostalgia có đồng bộ mod/host Java chưa hỗ trợ Horizon; dùng chức năng
LAN/server của engine. Nos Client tiếp tục phục vụ các bản Fabric 1.21.11 hiện có.

## Kết nối và thống kê

Đường chạy này đặt `HORIZON_TELEMETRY_URL=off`, `HORIZON_NO_HEARTBEAT=1`,
`HORIZON_NO_DISCORD=1` và `HORIZON_COSMETICS=0`. Không bật heartbeat đếm người chơi,
telemetry, presence cosmetic hoặc Discord riêng của Horizon. Lựa chọn thống kê launcher
không được chuyển thành đồng ý gửi telemetry game. Cơ chế launcher chỉ có sự kiện bản
cài hoạt động/ngày như [PRIVACY.md](PRIVACY.md), không sự kiện chạy game.

Kết nối phục vụ tải build/Minecraft, texture, xác thực Microsoft, truy cập server và
các chức năng mạng do người chơi sử dụng vẫn là luồng chức năng. Tài liệu này không
cam kết không có log/IP ở hạ tầng bên thứ ba hoặc mọi bản sửa engine do người dùng cài.

Nguồn chính thức: [Horizon](https://github.com/horizon-rust/horizon),
[Launch API](https://github.com/horizon-rust/horizon/blob/main/docs/api/launch-guide.md),
[telemetry](https://github.com/horizon-rust/horizon/blob/main/docs/telemetry.md).
Giữ nguyên nội dung build được tải từ upstream; giấy phép launcher và Nos không thay đổi.
