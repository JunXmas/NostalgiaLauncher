# Nostalgia 1.2.0rc35 — Forgotten Worlds 1.0.1

Forgotten Worlds 1.0.1 được tích hợp trong launcher và có file `.mrpack` tải riêng
trên trang release, kèm SHA-256 trong `SHA256SUMS`.

## Cài Forgotten Worlds

1. Vào **Bản chơi → Tạo bản chơi**.
2. Chọn **Forgotten Worlds**, Minecraft **1.21.11**, rồi bấm **Tạo bản chơi**.
3. Launcher cài Fabric Loader 0.19.5, Fabulously Optimized 12.3.0 và các mod client cần thiết.
4. Mở Minecraft → Multiplayer, chọn server **Junbob Mine — Forgotten Worlds** (`snow.pikamc.vn:25079`).

Để nhập riêng modpack, tải **Forgotten-Worlds-Optimized-1.21.11.mrpack** rồi kéo file
vào cửa sổ launcher hoặc chọn Nhập bản chơi. Bản chơi Forgotten Worlds đã tạo
có thể tiếp tục sử dụng.

Gói gồm Create Fly bản client đầy đủ, Friends&Foes, Serene Seasons, Streams Reflowing,
The Sift bản port 1.21.11 và các thư viện tương ứng. Phiên bản mod được ghim theo server;
Kotlin được thay thế bằng một bản duy nhất. The Sift là bản port không chính thức của mod MIT
của Mielon; metadata và tác giả của bản port được giữ nguyên.

Preset chỉ hỗ trợ Minecraft 1.21.11. RAM và thư mục chơi dùng lựa chọn trong phần
**Thiết lập nâng cao**. Java 21 được launcher chuẩn bị theo phiên bản game.

Mod quản trị và sinh địa hình ở phía server; client nhận địa hình khi kết nối.
Gói này dành để chơi server, không tái tạo toàn bộ bộ mod sinh thế giới trong chế độ một người chơi.
Luồng **Tối ưu / Optimized** vẫn cài Fabulously Optimized chuẩn cho các phiên bản được hỗ trợ.

## Lỗi đăng nhập đã xử lý trên server

Đã tái hiện lỗi `Mixin transformation of net.minecraft.class_3248 failed` do
SkinRestorer 2.11.0 xung đột với Cardboard 18. Server Junbob Mine đã tắt SkinRestorer
và khởi động lại; Simple_RTP, DonutSMP-Homes và SparkLogin hoạt động, TPS 20.0.
Chức năng phục hồi skin của SkinRestorer tạm ngừng.

Pack client giữ bộ mod đã ghim và được kiểm tra để loại các mod đăng nhập phía server.
Đã chạy Minecraft thực tế và kiểm tra lớp đăng nhập trước/sau khi khởi tạo mod.
Thử lớp đăng nhập phía server tái hiện lỗi khi có cả hai mod và thành công khi chạy riêng.
Việc kết nối từ máy người chơi cần được xác nhận bằng lần đăng nhập tiếp theo.

## Bộ cài

Có Windows setup.exe/portable, Linux AppImage/deb/rpm/tar.gz và macOS dmg/zip cho Apple Silicon
và Intel. Bộ cài và modpack có SHA-256 trong `SHA256SUMS`. Bản cập nhật không thay đổi tài khoản,
bản chơi hay world hiện có.
