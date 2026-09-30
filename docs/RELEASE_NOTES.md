Discord Rich Presence **tự chạy** — không phải thiết lập gì nữa.

## Trước: ba bước thủ công, nên gần như không ai bật

Muốn hồ sơ Discord hiện bạn đang chơi gì, bản cũ bắt bạn vào
[Developer Portal](https://discord.com/developers), tự tạo một Application, chép Application
ID về, dán vào CÀI ĐẶT, rồi mới gạt công tắc. Ba bước trước khi thấy được gì — một tính năng
mà không ai đi hết được đường thì coi như không tồn tại.

Nó còn im lặng theo hai kiểu nữa: chỉ hiện khi game đang chạy, và nếu lúc khởi động launcher
mà Discord chưa mở thì thôi luôn, mở Discord sau cũng không nối lại.

## Giờ: mở launcher là thấy

Không có gì để điền. Công tắc bật sẵn, launcher mang sẵn Application ID của nó.

- Mở launcher → hồ sơ Discord hiện **"Đang ở launcher"**.
- Vào game → **"Đang chơi &lt;bản chơi&gt;"** kèm đồng hồ đếm thời gian chơi.
- Đang ở phòng CHƠI CHUNG → **"Đang chơi chung với N người"**. Mã phòng **không** bao giờ lên
  Discord: đó là chìa khoá vào nhà bạn.
- Thoát game → quay về "Đang ở launcher", vì bạn vẫn đang ở launcher thật.
- Mở Discord sau launcher cũng được: cứ 30 giây launcher thử nối lại một lần.

Không thích thì gạt công tắc trong CÀI ĐẶT, presence biến mất khỏi hồ sơ ngay. Ai muốn hiện
tên app của riêng mình thì đặt biến môi trường `NOSTALGIA_DISCORD_APP_ID`.

## Vặt

- Trang tải trên GitHub Pages có giao diện mới (`docs/site/`).
- Thêm `.pre-commit-config.yaml`: chặn lỗi lint/định dạng/kiểu ngay lúc commit thay vì để CI
  bắt. Chỉ ảnh hưởng người sửa mã nguồn.
- Tầng lõi biết sinh mã QR cho URL xác minh khi đăng nhập Microsoft — giao diện chưa dùng,
  sẽ nối ở bản sau.
