# Forgotten Worlds trong Nostalgia Launcher

Trong **Tạo bản chơi**, chọn **Forgotten Worlds** và Minecraft **1.21.11**.
Launcher cài Fabric Loader 0.19.5, Fabulously Optimized 12.3.0 và bộ mod client
phù hợp với server Junbob Mine. Địa chỉ `snow.pikamc.vn:25079` có sẵn trong danh sách server.
RAM và thư mục chơi vẫn dùng lựa chọn trong hộp tạo bản chơi.

Gói 1.0.1 đi cùng launcher rc35 và có file `.mrpack` đính kèm trang release,
kèm SHA-256 trong `SHA256SUMS`. Có thể tiếp tục dùng bản chơi đã tạo bằng rc34.

Gói nằm tại `src/nostalgia/content/packs/forgotten-worlds-1.21.11.mrpack`.
Có thể nhập riêng file này bằng kéo thả; không cần API key của PikaMC.
PyInstaller đóng gói resource này cùng launcher.

## Các mod được thêm

- Create Fly 6.0.9-5 **bản client đầy đủ**, cùng phiên bản với bản server.
- Friends&Foes 4.0.27 và ResourcefulLib 3.11.1.
- Serene Seasons 21.11.0.4, GlitchCore 21.11.0.4 và TerraBlender 21.11.0.0.
- Streams Reflowing 2.14.1.
- The Sift 1.1.2, bản port không chính thức cho 1.21.11 từ bộ mod hiện có của server,
  và GeckoLib 5.4.5. Metadata, tác giả và giấy phép MIT của bản port được giữ nguyên.
- Fabric Language Kotlin 1.14.1 thay thế bản đi kèm FO; không cài hai bản cùng mod.

Các file công khai dùng URL và hash ghim từ Modrinth. The Sift port được lưu trong
`overrides/mods/` vì chưa có bản phát hành tương ứng trên Modrinth.

Cardboard, plugin Bukkit, AntiXray, BlueMap, Chunky và VSS ở phía server.
Terralith/Tectonic/Incendium/Nullscape và các mod sinh địa hình cũng ở phía server;
client nhận địa hình đã sinh khi kết nối. Gói này dành để chơi server, không tái tạo
toàn bộ bộ mod sinh thế giới trong chế độ một người chơi.

The Sift port khuyến nghị LambDynamicLights 4.12.2, nhưng bản phát hành cho Minecraft
1.21.11 hiện là 4.9.1, vốn có trong FO. Giữ nguyên 4.9.1; không cài mod cho phiên bản
Minecraft khác để đáp ứng một khuyến nghị. Cần kiểm tra thực tế phần ánh sáng của bản port.

## Tương thích đăng nhập

Lỗi `Mixin transformation of net.minecraft.class_3248 failed` ngày 2026-10-12
được tái hiện với SkinRestorer 2.11.0 và Cardboard 18 trên Minecraft 1.21.11.
Cardboard ghi đè phương thức đăng nhập mà SkinRestorer cần tiêm `waitForSkin`;
kết quả là `Critical injection failure`, `(0/1) succeeded`.

Server Junbob Mine đã tắt SkinRestorer và giữ file `.jar.disabled` để hoàn tác.
Chức năng phục hồi skin của mod này tạm ngừng. Cardboard, Simple_RTP,
DonutSMP-Homes và SparkLogin hoạt động sau restart, TPS 20.0.
SkinRestorer và Cardboard không nằm trong pack client.

Đã cài pack và chạy Minecraft thực tế bằng Java 21/Fabric 0.19.5; lớp đăng nhập
nạp thành công trước và sau khi các mod client khởi tạo. Kiểm tra lớp đăng nhập
phía server thất bại khi có cả SkinRestorer và Cardboard, thành công khi chạy
mỗi mod riêng. Cần xác nhận lần kết nối thực tế tiếp theo của người chơi;
môi trường kiểm tra không có kết nối TCP đến cổng Minecraft của PikaMC.

## Cập nhật bộ mod

Thay resource `.mrpack` bằng gói đã kiểm tra cho server. Nếu đổi Minecraft, cập nhật
`FORGOTTEN_GAME_VERSIONS` trong `content/builtin_pack.py`. Giữ phiên bản Fabric,
mod nội dung và phụ thuộc phù hợp với server, dùng bản client đầy đủ cho Create,
và không đưa cấu hình hosting, khóa API hay dữ liệu người chơi vào gói client.
