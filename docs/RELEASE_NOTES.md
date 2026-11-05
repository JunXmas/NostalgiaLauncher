# Nostalgia Launcher 1.2.3

- **English mặc định** cho cài mới; giữ ngôn ngữ đã lưu, có thể đổi trong Settings.
- Sửa nút **Nos Client** chồng chữ ở danh sách bản chơi rút gọn, hỗ trợ tiếng Việt/Anh
  và mức chữ 100–150%.
- Thêm mục **Giúp cải thiện Nostalgia**, ba trạng thái lựa chọn riêng, mẫu payload cục bộ
  và hộp thoại xin lựa chọn một lần khi dịch vụ đã sẵn sàng. Đóng X/Escape lưu từ chối.
- Thống kê tùy chọn mặc định **tắt**, chỉ có bản cài tham gia hoạt động/ngày UTC;
  **không thu sự kiện khởi chạy game**. Khi tắt, hủy tác vụ chưa gửi và xóa mã ngày.

**Trạng thái dịch vụ:** endpoint thống kê mới và lời mời đồng ý vẫn chưa kích hoạt.
Backend sửa việc ghi ngầm từ `/v1/me` chưa được deploy; backend production cũ có thể vẫn
đếm hoạt động tài khoản qua snapshot bạn bè cho đến khi bản backend đó được triển khai.
Không tuyên bố toàn bộ hạ tầng đã ngừng ghi dữ liệu hoặc không lưu IP.

Xem [quyền riêng tư](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.3/docs/PRIVACY.md)
và [schema](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.3/docs/usage-schema.json).
Lựa chọn thống kê không hạn chế đăng nhập, tải nội dung, cập nhật hoặc phòng chơi.

Giữ tự cập nhật Nos Client tương thích trên **Fabric 1.21.11**; Nos Client **0.4.3** bổ sung
font Be Vietnam Pro và cải thiện chữ lyrics/karaoke. Không thay profile Fabric hoặc các mod khác.

Có gói Windows x64, Linux x64, macOS Apple Silicon/Intel. Kiểm tra tại **Settings → Updates**;
macOS mở trang tải để cài. Mọi gói kèm SHA-256.
