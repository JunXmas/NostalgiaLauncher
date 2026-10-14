# Nostalgia 1.2.0rc38 — Kết nối P2P và skin Ely.by

Bản vá cải thiện bước tìm đường kết nối trực tiếp và sửa các dạng phản hồi
của Ely.by khiến thao tác lưu skin không hoàn tất.

## Chơi cùng bạn bè

- Cả host và khách chọn máy chủ STUN đang phản hồi, có máy dự phòng khi endpoint
  chính bị chặn hoặc không trả lời. STUN chỉ hỗ trợ tìm đường; dữ liệu game và
  modpack vẫn truyền trực tiếp bằng ICE/DTLS. Relay dữ liệu tiếp tục tắt.
- Thăm dò mạng có giới hạn thời gian và dọn socket khi huỷ. Khi không có STUN
  phản hồi, launcher vẫn giữ đường kết nối LAN.
- Kiểm lại thời hạn cấp quyền ở host sau khi chờ mạng; yêu cầu đã hết hạn
  không tạo thêm kết nối.

**Để thử bản vá:** cập nhật cả host và máy khách lên rc38, mở phòng và gửi lại
lời mời. Host vào world rồi chọn **Open to LAN → Start LAN World**; đợi launcher
nhận cổng LAN trước khi khách vào game. Nếu đồng bộ modpack, đợi đồng bộ hoàn tất.

Bản vá xử lý trường hợp STUN không truy cập được. Kết nối trực tiếp vẫn phụ thuộc
vào mạng hai đầu; mạng chặn UDP hoặc NAT không hỗ trợ P2P có thể cần đổi mạng.

## Lưu skin Ely.by

- Nhận ID từ URL trang skin và metadata bổ sung khi upload, thay vì yêu cầu
  phản hồi luôn có trường ID ở một vị trí cố định.
- Dùng đúng phương thức PUT của form sửa skin và giữ các trường xác thực của form.
- Nếu server chỉ trả URL sau khi đổi dáng tay, đọc lại metadata để xác nhận trước
  khi mặc skin. Xác nhận thất bại giữ nguyên skin đang mặc.

Chọn tài khoản Ely.by → chọn skin để xem trước → **Lưu thay đổi**. Nếu launcher
báo thiếu hoặc hết hạn phiên web, đăng nhập lại ngay tại mục skin rồi bấm Lưu.

## Bộ cài và kiểm chứng

Đủ Windows x64 setup/portable, Linux x64 AppImage/deb/rpm/tar.gz/zip và macOS
Apple Silicon/Intel dmg/zip. Các file có SHA-256 trong **SHA256SUMS**.
Nguồn cập nhật modpack độc lập của rc37 tiếp tục được sử dụng.

Các ca UDP, ICE/DTLS và giao thức upload dùng socket thật trên máy cục bộ hoặc
máy chủ HTTPS mô phỏng. Chưa xác nhận trên hai mạng Internet thực tế hoặc bằng
upload qua tài khoản Ely.by thật. Các bộ cài phải qua chạy thử tự động trước publish.

## English

- Select a responsive STUN endpoint before host/guest ICE setup, with bounded probes,
  fallback endpoints and cleanup on cancellation. Preserve LAN candidates when STUN is unavailable.
- Keep game/modpack transport on encrypted direct P2P; data relay remains disabled.
  Update both peers to rc38. Direct connectivity still depends on both networks.
- Handle Ely.by upload URLs and extra metadata, honor PUT form overrides and confirm
  the selected skin model before wearing it.
- Retain Windows, Linux and both macOS architectures, with SHA-256 checksums.
