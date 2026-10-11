# Ely.by: lỗi chứng chỉ máy chủ đăng nhập — 11/10/2026

Người dùng báo rc32 không đăng nhập Ely.by được trên Windows, với thông báo
`A required certificate is not within its validity period`. So sánh rc31 → rc32
không thấy thay đổi trong mã auth, TLS, đóng gói TLS hoặc phiên bản truststore 0.10.4.
Chưa biết người báo lỗi đã nâng cấp từ bản nào.

Báo cáo SSL Labs tại **14:46:31 UTC ngày 11/10/2026**, trạng thái READY, ghi nhận
`authserver.ely.by` tại `167.235.12.151` trả chứng chỉ có SAN đúng hostname nhưng:

- Chứng chỉ máy chủ `CN=www.authserver.ely.by` hết hạn **05/03/2026, 11:25:38 UTC**.
- Intermediate `GlobalSign GCC R6 AlphaSSL CA 2023` hết hạn **19/07/2026**.
- Các chuỗi Windows, Mozilla, Apple, Android và Java đều báo `validity check failed`.

Nguồn công khai: [SSL Labs](https://www.ssllabs.com/ssltest/analyze.html?d=authserver.ely.by).
Phép GET qua proxy kiểm tra của workspace cũng trả 503 với
`CERTIFICATE_VERIFY_FAILED` ở kết nối upstream. Đây là lỗi proxy xác minh upstream,
không phải phản hồi HTTP ứng dụng của Ely.by. GET `https://ely.by` trả 200;
trang chủ mở được không chứng minh chứng chỉ của máy chủ đăng nhập hợp lệ.

Kết quả phản ánh máy chủ/báo cáo ở thời điểm trên, có thể đổi khi Ely.by sửa cấu hình.
Không dùng dữ liệu này để ghim chứng chỉ, thay ngày giờ máy, bỏ xác minh TLS hoặc
tự gửi mật khẩu sang hostname khác. Ely.by cần cấp/cài lại chứng chỉ hợp lệ.

Launcher đổi thông báo lỗi chứng chỉ thành hướng dẫn tiếng Việt/English, giữ
mã và lỗi gốc trong log/exception để chẩn đoán. Kiểm thử HTTPS cục bộ đi qua luồng
đăng nhập Ely.by thật: chứng chỉ hết hạn, chưa có hiệu lực, sai hostname hoặc không
được tin cậy đều chặn request trước khi gửi mật khẩu; chứng chỉ hợp lệ vẫn đăng nhập.
Chưa kiểm thử đăng nhập bằng tài khoản thật trên máy Windows của người báo lỗi.
