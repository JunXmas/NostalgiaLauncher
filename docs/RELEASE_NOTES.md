# Nostalgia 1.2.0rc36 — Skin Ely.by và cập nhật Windows

Bản vá khôi phục việc đổi skin Ely.by ngay trong launcher và sửa bộ cập nhật
Windows cho các thư mục cài đặt cần quyền quản trị.

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

## Bộ cài và kiểm tra

Có Windows x64 setup/portable; Linux x64 AppImage, deb, rpm, tar.gz và zip;
macOS Apple Silicon/Intel dmg và zip. Gói Forgotten Worlds 1.0.1 vẫn được đính kèm.
Các file có SHA-256 trong **SHA256SUMS**; ảnh preview và tài liệu nội bộ không nằm
trong file phát hành. Bản này dùng cấu hình release tiêu chuẩn.

Luồng skin được kiểm tra với máy chủ HTTPS mô phỏng, gồm đăng nhập, upload,
áp dụng skin, phiên cũ, tài khoản nhập nhầm và 2FA; chưa kiểm tra upload bằng
tài khoản Ely.by thật. Các bộ cài được chạy thử tự động trước khi phát hành.

## English

- Fix Ely.by's internal OAuth client ID so skin sessions can be created correctly.
  Old accounts can sign in again directly from the skin panel without losing their preview;
  click **Save changes** after signing in to apply it. Includes 2FA and account identity checks.
- Fix protected Windows installations downloading Linux packages. Updates use the verified
  Windows installer and native UAC; cancelling UAC leaves the launcher open.
- Keep chat and friend-action errors visible across background refreshes until retrying
  or switching friends/sessions.
- All existing Windows, Linux and macOS packages remain available, along with Forgotten Worlds.
