# Nostalgia 1.2.0rc36 — Forgotten Worlds 1.0.2

Forgotten Worlds hướng tới sinh tồn công nghiệp: xây dây chuyền, tự động hóa với
Create và tra công thức bằng JEI. “Hoài niệm” là tên và phong cách hình ảnh của server.

## Cập nhật bản chơi đang dùng

1. Cập nhật launcher lên **1.2.0rc36**.
2. Đóng Minecraft, mở **Bản chơi → Quản lý bản chơi → Tổng quan**.
3. Bấm **Cập nhật modpack** trên bản chơi Forgotten Worlds cũ.

Launcher thêm JEI **27.48.0.106** và MezzConfig **0.6.8** vào bản chơi hiện tại.
Giữ thế giới, dữ liệu người chơi, thiết lập, phím tắt, danh sách server, shader,
resource pack, ảnh chụp, mod tự thêm, tên bản chơi và RAM đã chọn. Không cần tạo lại
bản chơi. Mod đã tắt hoặc xóa vẫn giữ trạng thái đó. Cấu hình mặc định chỉ được thêm
khi file chưa có; cấu hình đã dùng được giữ nguyên.

Các file do modpack quản lý chỉ được thay khi khớp bản đã cài. Mod tự sửa hoặc mod
trùng ID được báo rõ để người chơi chọn, không ghi đè. Tải và kiểm hash trước khi
áp dụng; lỗi hoặc hủy giữa chừng phục hồi bộ file và dấu vết phiên bản cũ. Các file
thay đổi được sao lưu tại `.nostalgia-sync-backups` trong thư mục đăng ký bản chơi.
Hỗ trợ cả bản chơi cài bằng rc35 và thư mục game riêng.

## Cài mới và sử dụng JEI

Chọn **Forgotten Worlds**, Minecraft **1.21.11** trong hộp tạo bản chơi.
Gói dùng Fabric **0.19.5**, Fabulously Optimized **12.3.0**, Create Fly **6.0.9-5**
và các mod nội dung phù hợp với server. Java 21 được launcher chuẩn bị.

Trong game, đưa chuột lên vật phẩm, bấm **R** để xem công thức hoặc **U** để xem
cách dùng. JEI và MezzConfig được cài ở client. File
**Forgotten-Worlds-Optimized-1.21.11.mrpack** tải riêng có cùng nội dung với gói
nhúng trong launcher và được ghi hash trong **SHA256SUMS**.

## Sửa cập nhật launcher trên Windows

Khi launcher nằm trong thư mục cần quyền quản trị, bộ cập nhật dùng bộ cài Windows
đúng phiên bản, kiểm SHA-256 rồi mở UAC. Hủy UAC thì launcher vẫn chạy. Bản cài vào
thư mục ghi được tiếp tục dùng cập nhật zip.

## Đổi skin Ely.by

- Sửa bước tạo phiên web Ely.by: gửi đúng client ID của OAuth thay vì để bước này
  thất bại dù tài khoản vẫn đăng nhập game được.
- Với tài khoản từ bản cũ hiện **No Ely.by web session**, chọn skin rồi bấm
  **Lưu thay đổi**. Launcher mở đăng nhập lại ngay tại mục skin; bản xem trước
  được giữ nguyên. Đăng nhập xong, bấm **Lưu thay đổi** để áp dụng.
- Hỗ trợ mã 2FA, kiểm tra đúng tài khoản đang chọn và báo lỗi nếu phiên web chưa
  được tạo thành công. Không cần xoá tài khoản khỏi launcher để phục hồi phiên.
- Một lần đăng nhập gặp lỗi web tạm thời không làm mất phiên đổi skin đã lưu.

## Cập nhật trên Windows

- Khi cần quyền quản trị, launcher chọn bộ cài Windows đúng phiên bản và kiến trúc,
  kiểm SHA-256 rồi mở bộ cài qua UAC để cập nhật đúng thư mục.
- Sửa lỗi tải gói Linux và báo thiếu **pkexec** trên Windows.
- Huỷ yêu cầu quyền sẽ giữ launcher đang mở. Nếu đang mắc lỗi cập nhật ở bản cũ,
  tải **setup.exe** bên dưới và chạy một lần để lên rc36.

## Thông báo chat rõ ràng hơn

Lượt làm mới nền không xoá thông báo gửi chat hoặc thao tác bạn bè thất bại.
Thông báo được xoá khi thử lại, chọn bạn khác hoặc đổi phiên đăng nhập.


Phiên Ely.by được kiểm tra bằng máy chủ HTTPS mô phỏng; chưa upload bằng tài khoản Ely.by thật.
