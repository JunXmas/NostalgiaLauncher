# Nostalgia Launcher 1.2.7

Bản vá sửa lỗi chuẩn bị Horizon (Rust) do hash manifest Minecraft và khôi phục lời mời thống kê cho người nâng cấp.

- Horizon dùng manifest Mojang nguyên bản theo research lock của build đã xác minh, cùng asset index riêng, thay vì đọc JSON Java có thể đã bị viết lại.
- Kiểm tra SHA-1 cache đầu vào ngay cả khi file sai có cùng kích thước; giữ kiểm tra hash của engine.
- Giữ nguyên metadata Java hiện có và world. Bản chơi Horizon bị lỗi chuẩn bị có thể thử Chơi lại sau khi cập nhật.
- Tái sử dụng thư viện, JDK và asset đúng hash; không yêu cầu xóa toàn bộ cache hoặc cài lại launcher.


- Trạng thái đồng ý cũ chưa có dấu xác nhận của đợt mở dịch vụ sẽ được hỏi lại một lần. Trong lúc chờ lựa chọn, launcher không gửi thống kê.
- Người chưa chọn nhận hộp thoại sau khi cửa sổ chính đã tải và launcher rảnh. Không chen vào đăng nhập, cài đặt, khởi chạy game hoặc hộp thoại khác.
- Giữ nguyên lựa chọn từ chối cũ. “Không gửi”, X và Escape tiếp tục lưu từ chối; không hỏi lại sau các lần mở hoặc cập nhật bình thường.
- Lựa chọn mới trong hộp thoại hoặc **Cài đặt → Giúp cải thiện Nostalgia** được lưu trên máy, không gắn tài khoản Google.
- Lỗi kiểm tra cập nhật đã kết thúc không còn chặn lời mời mãi khi launcher đã rảnh.

Thống kê vẫn chỉ có **bản cài tham gia hoạt động/ngày UTC**, phiên bản launcher, nhóm hệ điều hành và mã ngẫu nhiên trong ngày. Không thu sự kiện khởi chạy Minecraft, tài khoản, token, HWID, chat, server, world, danh sách mod hay log đầy đủ.

Việc xóa mã ngày và xác nhận lại có thể đếm lại một bản cài trong ngày chuyển đổi; không diễn giải thành người dùng mới. Không sửa số liệu lịch sử. Xem [hành vi và giới hạn quyền riêng tư](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.7/docs/PRIVACY.md).

Horizon (Rust) thử nghiệm, offline và skin Ely.by cục bộ từ 1.2.5 tiếp tục có trong bản này. Horizon không chạy mod Java/Nos Client hoặc xác thực Ely.by; xem [hướng dẫn Horizon](https://github.com/JunXmas/NostalgiaLauncher/blob/v1.2.7/docs/HORIZON.md).

Có đủ gói Windows x64, Linux x64, macOS Intel và Apple Silicon, kèm **SHA256SUMS**. Kiểm tra cập nhật trong Cài đặt; macOS cài thủ công qua trang tải.
