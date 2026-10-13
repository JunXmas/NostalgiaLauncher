# Forgotten Worlds — Optimized

Gói client tích hợp Minecraft **1.21.11**, Fabric Loader **0.19.5**, nền
Fabulously Optimized **12.3.0**. Phiên bản **1.0.2** đi cùng launcher **rc36**.
Hoài niệm là tên và phong cách hình ảnh; lối chơi hướng sinh tồn công nghiệp,
xây dây chuyền và tự động hóa với Create.

## Nội dung

- Create Fly 6.0.9-5 bản client đầy đủ.
- JEI 27.48.0.106 và thư viện MezzConfig 0.6.8, đúng bản Fabric 1.21.11.
- Friends&Foes 4.0.27, ResourcefulLib 3.11.1.
- Serene Seasons 21.11.0.4, GlitchCore 21.11.0.4, TerraBlender 21.11.0.0.
- Streams Reflowing 2.14.1.
- The Sift 1.1.2 port 1.21.11 và GeckoLib 5.4.5. Giữ metadata và giấy phép MIT.
- Fabric Language Kotlin 1.14.1, một bản duy nhất.

JEI: đưa chuột lên vật phẩm rồi bấm R để tra công thức hoặc U để tra cách dùng.
Các file công khai có URL và hash ghim từ Modrinth. The Sift port nằm trong
`overrides/mods/`. JEI và MezzConfig chỉ được thêm vào client.
Cardboard, plugin quản trị và mod sinh địa hình ở phía server.

## Cài và cập nhật

Cài mới: **Bản chơi → Tạo bản chơi → Forgotten Worlds → Minecraft 1.21.11**.
Nhập riêng: kéo file `.mrpack` trên trang release vào launcher. Gói được nhúng tại
`src/nostalgia/content/packs/forgotten-worlds-1.21.11.mrpack`.

Cập nhật bản cũ: cập nhật launcher rc36, đóng Minecraft, mở **Quản lý bản chơi →
Tổng quan → Cập nhật modpack**. Giao diện cũ có nút tương ứng trong **Sửa bản chơi**.
Không tạo lại bản chơi. Giữ thế giới và dữ liệu người chơi, thiết lập/phím tắt,
server, shader, resource pack, ảnh chụp, mod tự thêm và thông tin bản chơi.
Mod đã xóa hoặc tắt không tự cài lại/bật lại. Cấu hình chỉ thêm khi chưa tồn tại.

`.nostalgia-builtin-pack.json` ở thư mục đăng ký ghi hash và danh tính file do gói
quản lý. rc35 chưa có receipt được nhận diện bằng README và baseline 1.0.1 đã ghim.
Tải file mới vào staging và kiểm hash trước khi ghi. Mod do gói quản lý chỉ thay
khi còn nguyên hash; mod tự sửa hoặc trùng ID dừng cập nhật với thông báo rõ.
Các file thay đổi được sao lưu trong `.nostalgia-sync-backups`; journal khôi phục
file và receipt nếu cập nhật lỗi, bị hủy hoặc bị gián đoạn. Thư mục game riêng
cũng dùng cùng quy trình; dữ liệu tài khoản của launcher không bị chạm tới.

## Bảo trì

Thay resource `.mrpack` sau khi kiểm Minecraft/Fabric, phụ thuộc và kết nối thực tế.
Tăng `versionId` trong index; các cài mới ghi receipt của gói mới. Không đưa API key,
cấu hình hosting hoặc dữ liệu người chơi vào pack. Nếu đổi Minecraft hoặc loader,
cần quy trình chuyển phiên bản riêng; cập nhật tại chỗ chặn bản không tương thích.
