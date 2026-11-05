# Tự cập nhật Nos Client

Khi bật Nos cho một bản chơi Fabric 1.21.11, launcher kiểm tra release ổn định trên
`JunXmas/nos-client` trước khi bấm Chơi tiếp tục khởi động Minecraft. Chủ phòng cũng chuẩn bị
Nos trước khi chụp bộ mod để chia sẻ. Không cần phát hành launcher mới mỗi lần Nos có bản vá.

## Chọn và kiểm gói

- Đọc tối đa 100 release, bỏ draft/prerelease, so phiên bản số thay vì lấy jar đầu tiên.
- Nhận tên công khai `nos-client-X.Y.Z.jar` hoặc tên có hậu tố `+mc1.21.11`. File sources,
  verifier và gói của game khác không được chọn.
- Gói phải có SHA-256 từ digest của GitHub hoặc `SHA256SUMS`. Kiểm kích thước, toàn vẹn ZIP,
  mod ID, phiên bản trong jar, Minecraft và yêu cầu Java/Fabric trước khi cài.
- Cache mới nằm ở `nos-client/1.21.11/<sha256>/<tên jar>` trong data directory. Kiểm lại hash
  khi dùng cache, kể cả lúc mất mạng. Cache cũ được nhận sau khi kiểm ZIP/metadata; khi có mạng,
  bản khớp SHA-256 được chuyển sang layout mới mà không tải lại.

## Cài đặt và lỗi

File mới được tải vào vùng tạm rồi xác minh. Bộ mod được dựng bằng cơ chế staging/hardlink
của launcher, chỉ thay file Nos, sau đó tráo thư mục có khóa và biên nhận. Không ghi đè tại chỗ
vào hardlink của jar cũ. Bản trước được giữ trong `.nostalgia-nos-updates` để phục hồi nếu quá
trình bị gián đoạn; cơ chế lịch sử chung giới hạn ba lần gần nhất.

Jar Nos chép tay có tiền tố cũ hoặc được đổi tên nhưng vẫn mang metadata `nosclient` cũng được
nhận diện để không để hai mod cùng ID. Nếu jar không đổi thì không tráo thư mục hoặc tạo thêm
bản sao lưu. Mod và cấu hình không thuộc Nos giữ nguyên.

Nếu mạng/GitHub lỗi hoặc gói mới không hợp lệ, launcher dùng cache hay bản đang cài tương thích.
Bản đang cài mới hơn không bị hạ xuống bản cache cũ. Nếu không có bản tương thích nào đã xác
minh, báo lỗi chuẩn bị; công tắc bật lần đầu vẫn tắt và người chơi có thể thử lại. Hủy chuẩn bị
được truyền qua tải gói và kiểm trước commit. Cập nhật chỉ có hiệu lực cho lần khởi động kế tiếp.

Yêu cầu loader cao hơn bản chơi hiện có không tự thay profile Fabric. Với bản Nos cần loader
mới, launcher giữ bản tương thích trước đó; nếu chưa có thì báo người chơi kiểm tra Fabric.
Đây là cập nhật jar Nos; các phụ thuộc Fabric API của bản chơi vẫn theo bộ mod đang cài.

## Kiểm thử

Các ca trong `tests/nos_client` và `tests/ui/test_nos_toggle_flow.py` dùng jar ZIP thật, máy chủ
HTTPS cục bộ, thao tác giao diện, checksum lỗi, cache hỏng, mất mạng, hủy, khóa và giả lập lỗi
chép/tráo thư mục. Job Windows của CI chạy thêm bộ Nos bên cạnh updater launcher.

Kiểm thực tế độc lập đã nâng jar công khai 0.4.1 lên 0.4.2 từ GitHub; SHA-256 sau cài:
`c92596a48f4a198d0aaa6fbc70d471ed76f8f44aa7a16ee5b5417667f841418d`.
Kiểm lại lần hai không thay mtime của jar. Lượt này dùng data/config riêng.
