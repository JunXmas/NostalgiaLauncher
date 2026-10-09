# Cosmetic trong Minecraft: hướng triển khai

Trạng thái: thiết kế kỹ thuật, chưa có mod trong game. Hệ thống hiện tại chỉ có
khung avatar/nền hồ sơ và quyền nhận cosmetic qua giveaway. Không đổi skin/cape
Microsoft hoặc Ely.by; không ghi vào tài khoản Mojang.

## Các loại có thể làm

- Áo choàng: texture PNG do Nostalgia tự vẽ, mesh áo choàng và chuyển động theo nhân vật.
- Phụ kiện đầu: model gắn vào xương đầu, có thể là vương miện, tai hoặc vòng đội đầu.
- Đai/phụ kiện thân: model gắn vào thân; tư thế phải theo chuyển động của nhân vật.

Dùng mod client riêng. Người chơi khác cần cài mod tương thích để thấy phụ kiện.
Server Minecraft thông thường không cần plugin nếu mod chỉ bổ sung hiển thị.
Cần thử riêng shader, Elytra, áo giáp, model slim, góc nhìn thứ nhất và mod thay
player renderer. Không gọi đây là cape chính thức của Mojang.

## Phát hành và bảo trì

Bắt đầu bằng một phiên bản Minecraft/Fabric và áo choàng. Sau khi kiểm tra trong
game, mở rộng phụ kiện đầu/thân và các bản loader khác. Forge/NeoForge cần phần
render adapter riêng; không hứa một file mod chạy mọi phiên bản Minecraft.

Danh mục 3D riêng, không gán model vào ba ID trang trí hồ sơ hiện có. Mỗi cosmetic
có ID cố định, loại/slot, revision, model, texture, SHA-256, giới hạn render,
trạng thái active/retired/disabled và phạm vi loader/game tương thích. Tệp xuất từ
Blockbench phải được kiểm tra và chuyển sang định dạng dữ liệu do mod hiểu.
Không tải Java, script hoặc plugin thực thi từ danh mục cosmetic.

Giữ ID khi cập nhật texture/model. Retired ngừng tặng mới nhưng giữ quyền hiện
có; disabled không render. Cho phép rollback revision. Asset được cache theo hash,
không tải lại mỗi frame; model được bake một lần và render theo khoảng cách/tầm nhìn.
Giới hạn số vertex, độ phân giải, animation và request; ưu tiên atlas/batched draw.

## Tài khoản và quyền

Google giữ quyền sở hữu. UUID Minecraft là ánh xạ hiển thị cần xác minh bằng
phiên Microsoft/Ely.by thực, không tin tên/UUID do mod tự khai. Tài khoản offline
không được nhận danh tính cosmetic của người chơi khác chỉ bằng cách đặt cùng tên.

Mod nhận token giới hạn chỉ cho cosmetic, thời hạn ngắn, gắn phiên/UUID/device;
không nhận Google Client Secret, token quản trị hay bearer token đầy quyền của
launcher. Trao token qua cơ chế IPC bảo vệ trên máy, không qua đối số dòng lệnh.
Backend kiểm tra quyền mua/tặng và quyền trang bị; API nhìn người chơi khác chỉ
trả cosmetic đã trang bị, không trả email, giá mua hoặc dữ liệu thanh toán.

Không dùng một cờ Plus trong mod để mở khóa. Việc thu hồi được phản ánh ở lần
làm mới quyền và sau khi token hết hạn. Khi offline hoặc API lỗi, dùng quyền cache
có thời hạn, không mở mọi cosmetic. Thiết bị khác không kế thừa token phiên cũ.

Không thể bảo đảm người dùng không sửa mod để tự render phụ kiện trên máy mình.
Backend có thể bảo vệ quyền sở hữu, cấp phát chính thức và diện mạo mà những
client nguyên bản khác nhìn thấy; không thể khóa hoàn toàn một renderer chạy
trên máy do người dùng kiểm soát.

## Điều kiện trước khi đưa vào launcher

Mod phải được thử với tài khoản đã xác minh và hai client trong một thế giới,
bao gồm account Free nhận quà, tài khoản trả phí, thu hồi, đổi máy, mạng lỗi,
shader/Elytra/áo giáp và hiệu năng khi đông người. Cài mod là lựa chọn rõ ràng;
không tự sửa modpack mà người chơi chưa đồng ý.
