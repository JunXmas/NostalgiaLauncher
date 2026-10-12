# Forgotten Worlds trong Nostalgia Launcher

Trong **Tạo bản chơi**, chọn **Forgotten Worlds** và Minecraft **1.21.11**.
Launcher cài Fabric Loader 0.19.5, Fabulously Optimized 12.3.0 và bộ mod client
phù hợp với server Junbob Mine. Địa chỉ `snow.pikamc.vn:25079` có sẵn trong danh sách server.
RAM và thư mục chơi vẫn dùng lựa chọn trong hộp tạo bản chơi.

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

## Cập nhật bộ mod

Thay resource `.mrpack` bằng gói đã kiểm tra cho server. Nếu đổi Minecraft, cập nhật
`FORGOTTEN_GAME_VERSIONS` trong `content/builtin_pack.py`. Giữ phiên bản Fabric,
mod nội dung và phụ thuộc phù hợp với server, dùng bản client đầy đủ cho Create,
và không đưa cấu hình hosting, khóa API hay dữ liệu người chơi vào gói client.
