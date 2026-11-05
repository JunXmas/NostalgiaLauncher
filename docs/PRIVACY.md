# Quyền riêng tư và thống kê tự nguyện

Tài liệu này mô tả bản sửa trong repository. Backend mới **chưa được deploy**; chưa xác minh
toàn bộ cấu hình lưu log production. Luồng thống kê mới và lời mời đồng ý mặc định chưa kích hoạt.
Backend đang chạy bản cũ có thể vẫn đếm hoạt động tài khoản qua `/v1/me` cho đến khi chủ dự
án triển khai bản backend đã bỏ lệnh ghi ngầm. Cài đặt client không thể thay đổi hành vi
của backend cũ mà vẫn giữ nguyên chức năng bạn bè.

## Thu thập để trả lời câu hỏi gì?

Số tổng hợp theo phiên bản launcher và nhóm hệ điều hành giúp nhóm phát triển biết những
bản nào còn được sử dụng trong nhóm tự nguyện tham gia. Mục đích là ưu tiên kiểm thử,
phân bổ công sức sửa lỗi, quyết định tiếp tục hỗ trợ phiên bản/nền tảng nào và lập kế hoạch
cho các bản tiếp theo. Không dùng dữ liệu để lập hồ sơ từng người hoặc nhắm quảng cáo.

Lượng sử dụng không tự chỉ ra lỗi cụ thể hoặc chứng minh bản nào có nhiều lỗi hơn. Cần
đối chiếu với báo cáo lỗi và góp ý do người chơi chủ động gửi; thống kê này không thu log
hay gửi crash report thay cho người chơi. Số liệu chỉ mô tả nhóm đồng ý, không đại diện
toàn bộ người dùng launcher.

## Những kết nối khác nhau

| Luồng | Mục đích và dữ liệu | Liên quan lựa chọn thống kê |
| --- | --- | --- |
| Microsoft/Mojang, Ely.by, Google OAuth | Đăng nhập, phiên và hồ sơ phục vụ tài khoản; có thông tin định danh cần cho chức năng | Không phải đồng ý thống kê |
| Dịch vụ Nostalgia `/v1/me`, bạn bè, lời mời, hồ sơ | Tải dữ liệu người chơi yêu cầu, khóa mã hóa lời mời và phiên; bản mới không ghi analytics từ snapshot | Vẫn hoạt động khi từ chối |
| Phòng chơi, WebSocket ping, STUN/UPnP/P2P | Duy trì phòng/kết nối, đồng bộ nội dung sau lựa chọn của người chơi | Không phải thống kê; không bị tắt |
| Mojang, loader, Modrinth/CurseForge, skin/cape | Cài đặt, duyệt/tải nội dung và texture | Vẫn hoạt động |
| GitHub | Kiểm tra cập nhật launcher/Nos, feed trang chủ; có thể chạy khi chưa đăng nhập | Không phải sự kiện analytics |
| Sửa mod | Sau thao tác yêu cầu sửa, gửi phiên bản game/loader/Java, tên file và hash mod, metadata/dependency mod và chẩn đoán lỗi phụ thuộc đã rút gọn; kèm phiên xác thực dịch vụ | Luồng chức năng riêng, không gửi toàn bộ log hoặc đường dẫn cá nhân |
| Discord Rich Presence | IPC tới ứng dụng Discord cục bộ: PID, trạng thái, tên bản chơi và thời điểm; Discord có thể hiển thị cho người khác | Công tắc riêng, hiện vẫn bật mặc định; không suy diễn consent thống kê từ nó |
| `POST /v1/usage` mới | Chỉ bản cài đã đồng ý, một sự kiện hoạt động/ngày | Mặc định không gửi |

Không thấy cơ chế tự động upload crash report hoặc toàn bộ log trong mã launcher được kiểm.
Tài liệu không cam kết về telemetry riêng của Minecraft hoặc các mod bên thứ ba.
Worker cũ còn có presence trong Durable Object, giữ tên/trạng thái/phòng trong bộ nhớ để
tra cứu online; launcher hiện tại không gọi đường presence cũ này. Nó khác bảng analytics
tài khoản và endpoint thống kê tùy chọn mới.
Timer `_heartbeat` của `ServerBridge` chỉ cập nhật trạng thái giao diện/log server cục bộ,
không gửi request. Heartbeat WebSocket giữ kết nối là luồng riêng phục vụ phòng chơi.

## Lựa chọn được lưu trên máy

`settings.json` có `usage_choice_v1`: `unselected`, `declined` hoặc `accepted`. Chỉ giá trị
`accepted` cho phép gửi. Cài mới và các cờ cũ không rõ nghĩa đều là `unselected`, không gửi.
Lựa chọn không dựa vào Google, điều khoản, Discord hoặc tài khoản Minecraft; không đồng bộ
sang máy khác. Cập nhật bình thường giữ lựa chọn. Xóa cấu hình/cài lại có thể mất lựa chọn.

Sau khi endpoint đã được operator xác nhận hoạt động, người chưa chọn được hỏi một lần
khi cửa sổ chính đã dùng được và rảnh. Hoãn trong đăng nhập, tác vụ cài/nhập/cập nhật, khởi
chạy/chơi game, popup khác hoặc xử lý lỗi. Hai nút có cùng kiểu; không đặt sẵn đồng ý.
“Không gửi”, X và Escape đều lưu từ chối. Đã chọn trong Cài đặt thì không hỏi nữa.
Khi dịch vụ chưa sẵn sàng, không mở hộp mời đồng ý; xem mẫu trong Cài đặt vẫn dùng được.
Trang Cài đặt hiển thị “Chưa khả dụng” và lý do, thay cho công tắc bị khóa. Lựa chọn đã lưu
được giữ; vẫn có thể từ chối hoặc rút lại đồng ý khi dịch vụ chưa sẵn sàng.

Cài đặt → **Giúp cải thiện Nostalgia** cho thay đổi lựa chọn, xem dữ liệu minh họa và chính
sách. Từ chối không giảm chức năng. Mẫu dựng cục bộ từ đúng cấu trúc payload, dùng mã giả,
không mở endpoint thu thập và không tạo sự kiện chờ gửi.

## Contract duy nhất

Schema: [usage-schema.json](usage-schema.json). Endpoint là origin HTTPS đã xác nhận của
dịch vụ Nostalgia với đường dẫn chính xác `/v1/usage`. Không suy ra URL từ đăng nhập.
File `usage/defaults.json` hiện có endpoint rỗng và `ready: false`; không có request mới.
Operator chỉ cấu hình `NOSTALGIA_USAGE_ENDPOINT` cùng `NOSTALGIA_USAGE_READY=1`, hoặc file
đóng gói tương ứng, sau khi migration/backend và chính sách hạ tầng được kiểm tra.

```json
{
  "schema_version": 1,
  "event": "installation_active",
  "day": "2026-11-05",
  "launcher_version": "1.2.3",
  "os_group": "windows",
  "daily_id": "0123456789abcdef0123456789abcdef"
}
```

Đây là dữ liệu **minh họa**. Chỉ ngày UTC, phiên bản, nhóm OS (`windows`, `linux`, `macos`,
`other`), loại sự kiện và mã ngày được gửi. Không gửi tài khoản/email/token, tên máy,
HWID/MAC/serial, fingerprint, server, world, chat, log, danh sách mod hoặc phần cứng chi tiết.
Không có sự kiện chạy game, tín hiệu tạo Java process hay suy luận đã vào world.

“Hoạt động” ở đây nghĩa là launcher đang chạy khi đã đồng ý: kiểm một lần lúc khởi tạo
luồng và mỗi phút để nhận ngày UTC mới. Launcher để mở qua đêm có thể được tính cho ngày
mới, kể cả ở nền; không đo thao tác, thời lượng chơi hoặc suy ra người đang chơi Minecraft.

Mã 128 bit sinh ngẫu nhiên độc lập mỗi ngày UTC, giữ qua lần mở trong cùng ngày nếu cấu
hình còn nguyên; không có mã gốc cố định hoặc liên kết khách với tài khoản. Backend chỉ
lưu băm của ngày cộng mã để chống đếm lặp. Mỗi mã/ngày được chấp nhận tối đa một lần,
kể cả retry đồng thời hoặc đổi OS/phiên bản. Đây là **bản cài tham gia thống kê/ngày**,
không phải người hoặc thiết bị riêng biệt. Xóa dữ liệu, cài lại hoặc tắt rồi bật lại có
thể tạo mã mới. Không cộng các ngày để suy ra khách riêng biệt tuần/tháng hoặc retention.

## Tắt, lỗi mạng và lưu trữ

Khi tắt, dừng timer, hủy token và thế hệ tác vụ, xóa `usage-day.json`; không có hàng đợi
hay retry được lưu. Worker đọc lại lựa chọn ngay trước gửi; tác vụ cũ không hoạt động lại
khi bật sau đó. Không tạo dữ liệu chờ trong thời gian tắt. Bật chỉ tính hoạt động hiện tại
và về sau. Request đã bắt đầu rời máy có thể không thu hồi được.

Luồng gửi best-effort, tối đa một lần thử/ngày, không gửi bù. Lỗi thống kê không hiện popup
lỗi, không chặn chơi. Do mất mạng, hủy hoặc giới hạn lạm dụng, số liệu có thể thiếu.
Backend giới hạn 512 byte và allowlist chặt; không nhận Authorization/Cookie/query.
Giới hạn 120 request/phút/isolate và tối đa 5.000 mã/ngày giới hạn ghi D1, không lấy IP làm
khóa thống kê. Đây không thay thế WAF/giám sát vận hành.

Băm mã chống lặp đặt hạn **24 giờ**, cron dọn mỗi giờ; số tổng hợp giữ **90 ngày UTC**.
Đây là chính sách bảng hoạt động trong bản mã mới, phụ thuộc cron chạy thành công.
Không hứa tối đa 48 giờ trên mọi lớp: backup D1, log, trace, xuất log và cache hạ tầng
chưa kiểm chứng. Xóa bản ghi hoạt động không chứng minh bản sao lưu cũng đã xóa.

Kiểm tra read-only ngày 05/11/2026 qua API settings của ba Worker `nostalgia-payment-admin`,
`nostalgia-backend`, `nostalgia-multiplayer-relay`: không thấy cấu hình observability explicit,
`logpush: false`, không có tail consumer cấu hình. Điều này không chứng minh không có live
Tail, log hạ tầng khác hoặc IP được lưu. API liệt kê Logpush toàn account trả 403 với quyền
hiện có; không đọc nội dung log người chơi, query trace hoặc bản sao lưu D1.

Mã endpoint mới không log payload, IP hay tài khoản. Máy chủ/Cloudflare vẫn nhìn thấy IP
khi nhận kết nối; không khẳng định “không lưu IP” hoặc “ẩn danh hoàn toàn”. Worker Logs,
Tail/Logpush, reverse proxy, truy vấn D1, backup và thời hạn lưu thực tế cần được operator
kiểm tra trước khi kích hoạt. IP hiện còn được dùng riêng để chống lạm dụng đăng nhập,
không dùng làm định danh thống kê mới.

## Phân biệt lịch sử và dashboard

Trước bản sửa, backend `friend.snapshot()` gọi `recordActivity()` khi tải `/v1/me`, ghi
`analytics_activity(day, account_id, first_seen)` theo UTC+7 mà không có consent riêng.
Dashboard cũ có số tài khoản tuần/tháng/online; cleanup lịch sử là 400 ngày.
Bản sửa bỏ lệnh ghi, không đổi hoặc gắn lại nhãn các hàng lịch sử; chúng có khu vực riêng
ghi phương pháp cũ và UTC+7. Chính sách dọn lịch sử có sẵn được giữ, không đưa lịch sử vào v1.

Dashboard v1 ghi **Bản cài tham gia thống kê hoạt động/ngày**, ngày UTC hiện tại chưa hoàn
tất, không đại diện toàn bộ launcher. Lượt tải GitHub là số file tải, ở khu vực riêng;
không cộng với bản cài hoặc tài khoản. Không có khách riêng biệt tuần/tháng hay retention.

Tham khảo cơ chế nền tảng: [D1 batch](https://developers.cloudflare.com/d1/worker-api/d1-database/)
và [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/).
Đây không phải bằng chứng về cấu hình đang chạy của dự án; chưa deploy hoặc sửa dữ liệu production.
