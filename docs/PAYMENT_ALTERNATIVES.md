# Phương án nhận tiền với Vietcombank cá nhân

Đối chiếu tài liệu công khai ngày 07/10/2026. Chủ dự án xác nhận tài khoản nhận
là **cá nhân**. Chưa đăng ký dịch vụ, kết nối ngân hàng hay thay PayOS trong mã.
Plus vẫn tạm khóa; nút xác nhận của người chơi không phải bằng chứng đã nhận tiền.

| Phương án | Vietcombank cá nhân | Điều kiện và giới hạn |
| --- | --- | --- |
| Pay2S | Tài liệu có mẫu VCB cá nhân qua RPA | Dùng tên đăng nhập/mật khẩu Internet Banking. Có webhook/API đối soát. Đây là phương thức RPA, không đồng nghĩa API ngân hàng chính thức cho cá nhân. |
| SePay OneQR | Trang Vietcombank của SePay nêu doanh nghiệp/hộ kinh doanh | Cần hợp đồng OneQR với ngân hàng. Chưa có căn cứ xác nhận tài khoản cá nhân thông thường dùng được phương thức này. |
| SePay qua SMS | SePay có hướng dẫn phương thức SMS cho cá nhân/tổ chức | Cần ngân hàng cho thêm số nhận thông báo biến động, không phải số nhận OTP. Vietcombank không gửi SMS giao dịch dưới 50.000đ; không dùng làm nguồn duy nhất cho gói 29.000đ. |
| VietQR + đối soát thủ công | Có thể tạo QR nhận tiền vào tài khoản cá nhân | QR chỉ điền ngân hàng/số tiền/nội dung. Chủ dự án kiểm tra tiền thật trong ngân hàng rồi backend cấp quyền cho tài khoản Google. Không tự động. |

## Đề xuất

Nếu cần giữ Vietcombank cá nhân và tự động ngay, **Pay2S là ứng viên có tài liệu
phù hợp rõ nhất trong các nguồn đã kiểm tra**. Tuy nhiên, việc cung cấp thông tin
đăng nhập ngân hàng cho hệ thống RPA là một đánh đổi đáng cân nhắc. Chủ dự án cần
xác nhận kết nối VCB hiện còn khả dụng, phạm vi đọc giao dịch và điều kiện lưu thông
tin đăng nhập với nhà cung cấp trước khi quyết định. Không đưa mật khẩu ngân hàng
vào launcher, repository hay chat.

Bảng giá Pay2S đang công bố: Free 1 tài khoản ngân hàng, **50 giao dịch/tháng**;
Basic **150.000đ/tháng**, 1 tài khoản ngân hàng, không giới hạn giao dịch. Đây là
phí nhà cung cấp, chưa kết luận phí ngân hàng/thuế hoặc chất lượng kết nối thực tế.
Ở giá 29.000đ, khoảng 6 lượt mua/tháng mới vượt phí Basic, trước các chi phí khác.

Trong lúc hoàn thiện Google và chưa chốt nhà cung cấp, giữ **Plus tạm khóa**.
Nếu sau này cần mở bán thử mà chưa muốn dùng RPA, VietQR + duyệt thủ công là
phương án ít phụ thuộc kết nối ngân hàng hơn. Nếu chuyển sang tài khoản hộ kinh
doanh/doanh nghiệp, có thể đánh giá lại SePay OneQR.

Không xem Casso/VNPAY là lựa chọn đã xác nhận cho VCB cá nhân: các trang đã đọc
chưa đủ chứng minh phương thức kết nối phù hợp trường hợp này.

## Khi tích hợp sau này

Backend tạo đơn gắn với Google user ID, số tiền và mã đơn duy nhất. Webhook phải
xác thực theo tài liệu nhà cung cấp, so khớp tiền vào đúng tài khoản, nội dung đơn
và số tiền; lưu ID giao dịch để chống cấp quyền hai lần. API đối soát xử lý thông
báo thiếu/trùng. Chỉ backend ghi entitlement và cấp quyền tính năng từ máy chủ;
launcher chỉ đọc trạng thái. “Tôi đã chuyển khoản” chỉ yêu cầu kiểm tra lại đơn.
Không thể bảo đảm client mã nguồn mở không bị sửa; quyền dịch vụ trên máy chủ
mới là phần có thể kiểm soát thực chất.

## Nguồn chính thức

- [Pay2S — thêm ngân hàng, mục 1.4 mẫu cá nhân VCB/VTB qua RPA](https://docs.pay2s.vn/partner/bank.html).
- [Pay2S — API Open Banking và cách kết nối](https://pay2s.vn/open-api-banking).
- [Pay2S — bảng giá](https://pay2s.vn/bang-gia).
- [Pay2S — webhook, token xác thực và cấu trúc giao dịch](https://docs.pay2s.vn/webhook/tai-lieu-ky-thuat.html).
- [SePay — Vietcombank OneQR, điều kiện doanh nghiệp/hộ kinh doanh](https://sepay.vn/vietcombank.html).
- [SePay — thêm tài khoản, các phương thức API và SMS](https://docs.sepay.vn/them-tai-khoan-ngan-hang.html).
- [Vietcombank — SMS Banking](https://vietcombank.com.vn/vi-VN/KHCN/SPDV/Ngan-hang-so/SMS-Banking).
- [Vietcombank — phạm vi thông báo SMS, trang 2: ngưỡng 50.000đ](https://vietcombank.com.vn/-/media/Project/VCB-Sites/VCB/KHCN/San-pham-Dich-vu/Ngan-hang-so/Tai-lieu-Ngan-hang-so/VCB-SMS-Banking/VCB-CN-Pham-vi-thong-bao-dich-vu-SMS-chu-dong.pdf).
- [VietQR — tạo mã QR nhận chuyển khoản](https://vietqr.io/).
