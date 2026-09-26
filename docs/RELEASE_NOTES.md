Bản vá cho 1.1.0 — ba lỗi được sửa và một tính năng cũ quay lại.

## CHƠI CHUNG vào được phòng thật sự

Trước đây world của bạn hiện trong tab LAN của Minecraft nhưng bấm vào là "Connection
Refused": Minecraft nối qua IP card mạng (192.168.x) còn proxy của launcher chỉ nghe
127.0.0.1. Proxy nay nhận kết nối từ chính máy bạn qua mọi card mạng — và vẫn đóng sập
cửa với bất kỳ máy nào khác cùng LAN. Đã kiểm trọn vòng trên máy thật qua relay đang chạy.

## ⚠ Windows: bản này cần cài tay MỘT lần

Bộ tự cập nhật của 1.0.15–1.1.0 trên Windows bị hỏng (script tráo thư mục chết im lặng —
xem bên dưới), nên nó không tự kéo được bản này về. Tải `nostalgia-1.1.1-windows-x64-setup.exe`
(hoặc `.zip`) ở dưới và cài đè. Từ 1.1.1 trở đi tự cập nhật chạy bình thường.

## Tự cập nhật trên Windows chạy lại được

Script tráo thư mục cũ là batch chạy qua `cmd.exe`, chết theo ba đường cùng lúc và đều
im lặng: `timeout /t` thoát ngay khi không có bàn phím gắn vào, `cmd.exe` đọc script sai
bảng mã khi tên người dùng Windows có dấu tiếng Việt, và `move` bỏ cuộc khi Defender còn
giữ file exe vài giây sau khi launcher thoát.

Script nay là PowerShell (sẵn trên mọi Windows 10/11): đọc đúng UTF-8, chờ launcher cũ
tắt có giới hạn thời gian, thử lại khi file còn bị giữ, và chép hỏng thì trả lại nguyên
bản cũ — không bao giờ mất launcher. CI cũng chạy test bộ tự cập nhật trên Windows thật
từ nay.

## Thẻ hành tinh quay lại — khi thanh bên thu gọn

Thanh bên có nút **THU GỌN** mới. Thu gọn còn cột icon, và ở trang chủ sáu mục điều hướng
bay ra thành sáu thẻ neo vào các hành tinh trong ảnh nền vũ trụ. Rê chuột vào thẻ là thẻ
nhấc lên và **hành tinh của nó sáng quầng**. Mở thanh bên lại thì các thẻ nhường chỗ.

## Nút "Dùng" hiện lại khi hai tài khoản trùng tên

Nếu bạn đăng nhập một tài khoản Microsoft và một Ely.by **cùng tên**, trang TÀI KHOẢN
không hiện nút **Dùng** ở đâu cả — cả hai hàng đều tự nhận là "đang dùng" vì danh tính
khoá theo tên. Bản này khoá theo `account_id`:

- Nút Dùng hiện lại, và bấm nó chạy đúng tài khoản ở hàng đó (trước đây bấm ở hàng
  Ely.by vẫn chạy game bằng tài khoản Microsoft).
- Xoá tài khoản chỉ gỡ đúng một hàng — không mất vé đăng nhập của tài khoản trùng tên.
- CLI `--account Ten` gõ tay vẫn dùng được như cũ.

Không cần làm gì với dữ liệu — `accounts.json` cũ đọc được nguyên.
