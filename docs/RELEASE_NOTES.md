Đổi skin và cape **ngay trong launcher**, không phải mở trình duyệt nữa.

Trước bản này, trang TÀI KHOẢN chỉ *hiện* skin. Đổi thì vẫn phải sang trang web — nên phần
skin của launcher gần như vô dụng. Từ 1.1.4, bấm **Thêm skin** là skin đổi thật trên máy chủ,
bạn bè trong game nhìn thấy.

## Ely.by: upload skin thẳng từ launcher

Chọn file PNG → launcher gửi lên ely.by, đặt làm skin đang mặc, rồi tải lại để ảnh trong
launcher khớp với thứ người khác thấy trong game (qua authlib-injector). Cùng một tài khoản,
cùng một skin, dù bạn đổi ở launcher hay ở trang web.

Cần đăng nhập lại tài khoản Ely một lần sau khi cập nhật: launcher phải có phiên web mới
upload được, mà phiên đó chỉ lấy được lúc đăng nhập. Tài khoản cũ vẫn chơi được bình thường,
chỉ riêng nút đổi skin sẽ báo "đăng nhập lại tài khoản này để bật đổi skin".

Mật khẩu chỉ đi thẳng tới `account.ely.by` qua TLS và **không được lưu** — launcher chỉ giữ
vé phiên. Vé hết hạn thì báo rõ để bạn đăng nhập lại, chứ không lặng lẽ đổi mỗi ảnh hiển thị
trong launcher rồi để bạn tưởng đã xong.

Nút "Đổi skin ở ely.by ↗" đã bị gỡ: hai nút cùng làm một việc thì chỉ tổ phải đoán nút nào
mới thật.

## Microsoft: chọn và gỡ cape

Tab **Cape** liệt kê những cape tài khoản bạn sở hữu. Bấm một cái để mặc, bấm lại cái đang
mặc (viền xanh, dấu ✓) để gỡ ra. Danh sách chỉ tải khi bạn mở tab — đa số người chơi không có
cape nào, không việc gì bắt máy họ chạm mạng.

Cape không upload được: Mojang phát theo sự kiện (Migrator, Vanilla…) chứ không cho tự làm.
Launcher chỉ chọn trong số bạn đã có. Không có cái nào thì tab hiện đúng như vậy.

Ely.by không có API cape nên phần này chỉ dành cho tài khoản Microsoft.

## Vặt

- Vá cảnh báo Qt `Unable to assign [undefined] to QUrl` ở ô xem trước cape.
