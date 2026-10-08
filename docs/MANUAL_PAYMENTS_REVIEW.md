# Giao diện duyệt Vietcombank — source review

Backend có trang quản trị riêng: chủ đăng nhập Google rồi thêm/thu hồi người duyệt. Xem hướng dẫn ở repo `JunXmas/nostalgia-backend`, `account-service/MANUAL_PAYMENTS.md`. Đơn gắn với tài khoản Google, giá catalog máy chủ, nội dung và QR riêng; ảnh biên lai hay nút tự báo chuyển tiền không cấp quyền.

Client hỗ trợ response `manual_review` và `submitted` là boolean. QR VietQR được dựng cục bộ; **Đã chuyển khoản · Gửi duyệt** gọi `POST /v1/plus/orders/:id/submit` và tải lại đơn. Sau đó hiện **Chờ duyệt thanh toán**, giấu QR, thăm dò máy chủ 30 giây khi cửa sổ mở, giữ đơn khi hết thời gian quét; chỉ phản hồi paid hợp lệ từ backend mới hiển thị thành công. Giá/thông tin người nhận/mã đơn bị thay đổi hoặc trạng thái submitted bị lùi sẽ bị từ chối.

Gateway payOS cũ vẫn dùng quy trình kiểm tra của nhà cung cấp. Microsoft/Ely.by/skin và phiên Google launcher giữ luồng hiện tại.

Runtime phát hành hiện vẫn khóa Plus/thanh toán theo yêu cầu tạm dừng trước đây; source không tự mở thu tiền, không thêm một khóa quản trị trong launcher. Chưa build installer, tạo draft/release hay deploy backend. Chỉ kết nối gateway cho runtime khi chủ quyết định mở Plus sau cấu hình backend đầy đủ.

Đã kiểm tra gateway HTTPS giả, Qt/QML tương tác thật, yêu cầu duyệt không cấp quyền, giữ trạng thái chờ duyệt sau khi hết giờ, hồi quy QR/receipt 100%–150%, kiến trúc và kiểu. Ảnh preview nằm ngoài repo/release; người mua và các mã giao dịch trên ảnh là dữ liệu thử.
