Bản vá cho 1.1.2 — sửa lỗi tự cập nhật trên Windows, từ báo cáo của người chơi: bấm
**Cập nhật** thì launcher tắt và không bao giờ mở lại.

## ⚠️ Người dùng Windows: bản này phải cài TAY một lần

Bản vá nằm trong 1.1.3, nhưng thứ chạy lúc bạn bấm cập nhật là bộ cập nhật của bản **đang
cài** — tức bản còn lỗi. Nó vẫn sẽ tắt launcher rồi không mở lại.

Cách cài: tải `nostalgia-1.1.3-windows-x64-setup.exe` ở dưới, chạy, cài đè lên bản cũ. Dữ
liệu (tài khoản, bản chơi, mod, world) nằm ở `%APPDATA%\nostalgia` nên **không mất**.

Từ 1.1.3 trở đi nút Cập nhật chạy đúng. Chỉ phải làm tay lần này.

Người dùng Linux và macOS không bị lỗi này — cập nhật như thường.

## Bấm cập nhật xong app không mở lại nữa — đã sửa

Launcher không tự ghi đè chính mình được trong lúc đang chạy, nên nó viết một script tráo
thư mục, thoát, rồi script đổi tên thư mục cài và chép bản mới vào.

Chỗ sai: khi chạy script đó, launcher không nói cho nó biết phải đứng ở thư mục nào, nên
script thừa hưởng thư mục làm việc của launcher. Lối tắt trên Desktop không đặt thư mục làm
việc, nên Windows lấy mặc định là **chính thư mục cài**. Windows thì không cho đổi tên thư
mục nào đang là thư mục làm việc của một tiến trình còn sống — script tự khoá đúng thứ nó
định dời. Nó thử lại 30 lần trong 30 giây rồi bỏ cuộc, mà launcher đã thoát từ trước.

Các lớp vá: launcher chỉ định thư mục trung lập khi chạy script; script tự đứng ra chỗ trung
lập trước khi đụng vào thư mục cài; khi mở lại launcher thì chỉ rõ thư mục cài mới thay vì
để nó thừa hưởng thư mục tạm; và lối tắt của bộ cài từ nay đặt sẵn thư mục làm việc ra
ngoài thư mục cài — nguyên nhân gốc bị bịt ngay từ lúc bấm lối tắt.

Thêm nữa: từ nay **hỏng bước nào script cũng mở lại launcher** (miễn là thư mục cài còn
lành). Trước đây bất cứ bước nào trục trặc — phần mềm diệt virus giữ file, ổ đầy, thư mục
đang mở trong Explorer — là script bỏ đi im lặng và bạn ngồi nhìn màn hình trống. Nay xấu
nhất bạn cũng chỉ mất bản cập nhật, không mất launcher.

### Và một lý do nữa để lỗi này không chết hẳn lần sau

Script chạy sau khi launcher đã thoát, không có cửa sổ, không in ra đâu cả — hỏng là hỏng
câm. Mọi lần sửa trước đều là đoán từ triệu chứng "tắt rồi không mở lại", vì không có gì
khác để đọc.

Nay script ghi nhật ký cạnh chính nó:
`%APPDATA%\nostalgia\data\updates\apply-update.log`. Có giờ, có bước đang làm, và có câu lỗi
thật của Windows. Lần sau nếu còn hỏng, gửi file đó là biết ngay chỗ nào — không phải đoán
nữa.

## Ô CỘNG ĐỒNG trên thanh bên

Thanh bên có thêm một ô dẫn thẳng tới máy chủ Discord của Nostalgia. Trước đó địa chỉ ấy
không nằm ở đâu trong launcher, muốn hỏi một câu phải tự đi tìm.

Ô nằm dưới vạch ngăn, tách khỏi bảy mục trên nó, và không sáng lên khi bấm: bảy mục kia đổi
trang bên phải, ô này mở trình duyệt rồi bạn vẫn đứng nguyên ở trang cũ. Bản điện thoại cũng
có mục này trên rail dọc, cùng một link.

---

Cập nhật: Linux và macOS `.AppImage`/`.tar.gz` tự tải được bản này. Bản macOS `.app` và bản
chạy từ mã nguồn mở trang tải như trước. **Windows: xem phần cảnh báo ở đầu.** Mọi gói đều
phải khớp `SHA256SUMS` mới được cài.
