# Chơi chung và đồng bộ modpack — bản review

Ngày kiểm tra: 2026-10-06. Thay đổi chỉ nằm trong workspace; chưa push, build installer,
release hoặc deploy Worker.

## Kết nối và modpack

- Launcher gửi WebSocket ping mỗi 25 giây, chờ đúng pong trong 15 giây. Mất pong đóng
  socket và dọn task; host trở về trạng thái nghỉ, báo lỗi thay vì giữ phòng giả đang hoạt động.
- Dừng trong lúc đang vào phòng cũng hủy luồng bắt tay. Timeout bắt tay tính cho cả quá trình,
  thay vì bắt đầu lại sau mỗi mảnh dữ liệu.
- Relay riêng được chuyển sang Durable Object WebSocket Hibernation API. Socket attachments
  lưu vai trò, mã stream, vé host và bộ đếm stream; khi object thức dậy, kết nối được khôi phục.
  Đây là cách xử lý mất trạng thái khi object ngủ, chưa phải bằng chứng nguyên nhân của báo cáo 15 phút.
- Bộ lọc cho phép gói Handshake đến 1.024 byte, phù hợp hostname UTF-8 và dấu mở rộng Forge.
  Dữ liệu FML, registry và mod được chuyển nguyên vẹn, không viết lại giao thức Forge.
- Trang Chơi chung có nút chép `127.0.0.1:cổng` để dùng Direct Connection khi modpack không
  hiển thị LAN. Hai máy vẫn cần cùng game, loader và bộ mod tương thích.

Không tìm thấy bộ đếm 900 giây trong launcher hoặc mã relay ở kho riêng. Chưa có log lỗi
Minecraft của người chơi để kết luận nguyên nhân modpack không vào được hoặc ngắt đúng 15 phút.

## Một host Plus, khách miễn phí

1. Host mở LAN và phòng như thường, chọn đúng bản chơi rồi chia sẻ ảnh chụp modpack.
2. Máy chủ kiểm phiên tài khoản ủng hộ và vé bí mật do relay cấp riêng cho socket host.
3. Host gửi file vào R2; chỉ mục chỉ xuất hiện khi upload hoàn tất và file khớp SHA-256.
4. Khách nhập cùng mã phòng 18 ký tự, không cần phiên Plus. Ô **Đồng bộ modpack với chủ phòng**
   hiển thị Minecraft, loader, số file và dung lượng. Nếu host chia sẻ muộn, launcher kiểm tra lại
   mỗi 8 giây đến khi có chỉ mục; lỗi dịch vụ dừng polling, cho phép kiểm tra thủ công.
5. Khách chủ động bấm đồng bộ. Launcher tải/kiểm hash, cài đúng game và loader bằng các nguồn
   cài đặt có sẵn, rồi đăng ký bản chơi mới. Không ghi đè bản chơi cũ; lỗi/huỷ không đăng ký pack dở.

Ảnh chụp chỉ lấy `mods`, `config`, `defaultconfigs`, `kubejs`, `scripts`, `resourcepacks`,
`shaderpacks`. Không lấy `saves`, `logs`, tài khoản launcher, options hoặc kho game/Java dùng chung.
Host cần kiểm tra cấu hình mod trước khi chia sẻ vì cấu hình mod có thể chứa thông tin riêng.
Không gửi JSON khởi động, classpath hoặc Java của host cho khách.

Giới hạn: 1 GiB tổng, 64 MiB/file, 2.000 file; một ảnh chụp bất biến cho mỗi phòng, thời hạn
download 4 giờ. Đóng/mở phòng để chia sẻ ảnh mới. Relay vẫn giới hạn 16 kết nối game đồng thời;
khách không phải mua Plus. Thời hạn đồng bộ không đóng kết nối chơi game.

## Ranh giới bảo vệ Plus

- Backend xác minh Plus ở mỗi request upload/commit và quyền của host ở mỗi lần khách lấy
  chỉ mục hoặc file. Quyền hết hạn/thu hồi, phòng đóng, vé host khác hoặc mã lời mời sai đều bị từ chối.
- Vé host chỉ được cấp cho socket đã giữ phòng. Biết room ID không đủ để đăng ký pack.
- Khách gửi HMAC riêng cho đồng bộ, không gửi nguyên mã phòng/secret tới API. HMAC này là quyền
  tải của khách trong phòng, không dùng được làm proof bắt tay Minecraft hay tạo phòng Plus khác.
- Worker `plus-authorizer` chỉ đọc session băm SHA-256 và entitlement trong D1. Không có API
  để launcher ghi `paid`, `plus`, hay thời hạn quyền. Sửa giao diện/cờ local không cấp quyền D1.
- File giới hạn dung lượng, đường dẫn, symlink, tên Windows đặc biệt, đường dẫn trùng và hash.
  Không chấp nhận chuyển hướng HTTP hoặc lỗi mạng như một sự xác nhận quyền.

Không có bảo vệ tuyệt đối cho mã hoặc file trên máy người dùng. Người dùng có thể tự sao chép
modpack hay dựng một dịch vụ khác. Bảo vệ ở đây là quyền sử dụng **dịch vụ đồng bộ của dự án**;
không cấm cách chia sẻ thủ công vốn thuộc bản free.

## Cấu hình còn thiếu để dùng thật

Kho backend local: `/workspace/NostalgiaBackend` (kho riêng `JunXmas/nostalgia-backend`).
Đã có relay, R2 adapter, schema D1 và authorizer đọc quyền. Chưa tạo tài nguyên Cloudflare,
chưa deploy, và chưa có backend đăng nhập/thanh toán thật cấp session/ghi entitlement sau
xác minh giao dịch. Bấm “đã chuyển khoản” không tạo entitlement.

Trong preview, thêm `--room-sync-url https://<relay đã cấu hình>` vào runner. Host dùng thêm
`--plus-url` và `--plus-session-file`; khách chỉ cần `--room-sync-url`. Các tham số là đường
nối cho người phát triển, không phải luồng đăng nhập Plus hoàn chỉnh của người dùng cuối.

Giao diện đồng bộ được gắn vào preview. Bản release không tự bật dịch vụ trả phí chưa được cấu hình.

## Bằng chứng kiểm tra

- Relay TCP giả: một kết nối liên tục 1.020 giây, 52 lượt trao đổi; ping/pong và payload Forge.
- Runtime workerd cục bộ qua WSS: bài kiểm tra 1.020 giây, log trong
  `/workspace/scratch/multiplayer-workerd-soak.log`, cùng một kết nối và 52 lượt trao đổi, PASS.
  [Log hai bài soak](preview/minimal/multiplayer-soak.txt) được lưu cùng bản review.
- Node/Miniflare: chuyển tiếp byte, chống chiếm host, dựng lại state từ attachments,
  publish/commit/download, cờ Plus giả, vé giả, mã sai, thu hồi quyền, D1 authorizer và
  relay nối authorizer D1 thật trong runtime test.
- Qt/HTTPS/R2: host có session Plus **mẫu**, khách không có session, hiện offer rồi tải
  file thật vào bản chơi mới. Bước cài game/Forge được mock, không khởi động Minecraft.
- Ảnh UI từ Qt OpenGL ở 1.440×900 và 1.024×600, chữ 100%/150%, không có cảnh báo QML.
- QA cuối: 115 kiểm tra Python/Qt/kiến trúc, 15 kiểm tra Qt OpenGL và 11 kiểm tra Node/workerd;
  Ruff và mypy (415 file) qua. Các bộ có một phần kiểm tra trùng nhau, không cộng thành tổng duy nhất.
- Thử relay đang deploy qua proxy môi trường ngắt sau khoảng 2 phút. Không dùng kết quả này
  để xác nhận nguyên nhân 15 phút hoặc tuyên bố lỗi trên máy người chơi đã được giải quyết.

Ảnh review (dữ liệu có nhãn PREVIEW):

- [Host chia sẻ](preview/minimal/multiplayer-plus-host.png)
- [Khách miễn phí](preview/minimal/multiplayer-free-guest.png)
- [Màn hình nhỏ 150%](preview/minimal/multiplayer-free-guest-small-150.png)
- [Đồng bộ hoàn tất](preview/minimal/multiplayer-sync-complete.png)
