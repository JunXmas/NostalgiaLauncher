# Nostalgia 1.2.0rc36 — Forgotten Worlds 1.0.2

Forgotten Worlds hướng tới sinh tồn công nghiệp: xây dây chuyền, tự động hóa với
Create và tra công thức bằng JEI. “Hoài niệm” là tên và phong cách hình ảnh của server.

## Cập nhật bản chơi đang dùng

1. Cập nhật launcher lên **1.2.0rc36**.
2. Đóng Minecraft, mở **Bản chơi → Quản lý bản chơi → Tổng quan**.
3. Bấm **Cập nhật modpack** trên bản chơi Forgotten Worlds cũ.

Launcher thêm JEI **27.48.0.106** và MezzConfig **0.6.8** vào bản chơi hiện tại.
Giữ thế giới, dữ liệu người chơi, thiết lập, phím tắt, danh sách server, shader,
resource pack, ảnh chụp, mod tự thêm, tên bản chơi và RAM đã chọn. Không cần tạo lại
bản chơi. Mod đã tắt hoặc xóa vẫn giữ trạng thái đó. Cấu hình mặc định chỉ được thêm
khi file chưa có; cấu hình đã dùng được giữ nguyên.

Các file do modpack quản lý chỉ được thay khi khớp bản đã cài. Mod tự sửa hoặc mod
trùng ID được báo rõ để người chơi chọn, không ghi đè. Tải và kiểm hash trước khi
áp dụng; lỗi hoặc hủy giữa chừng phục hồi bộ file và dấu vết phiên bản cũ. Các file
thay đổi được sao lưu tại `.nostalgia-sync-backups` trong thư mục đăng ký bản chơi.
Hỗ trợ cả bản chơi cài bằng rc35 và thư mục game riêng.

## Cài mới và sử dụng JEI

Chọn **Forgotten Worlds**, Minecraft **1.21.11** trong hộp tạo bản chơi.
Gói dùng Fabric **0.19.5**, Fabulously Optimized **12.3.0**, Create Fly **6.0.9-5**
và các mod nội dung phù hợp với server. Java 21 được launcher chuẩn bị.

Trong game, đưa chuột lên vật phẩm, bấm **R** để xem công thức hoặc **U** để xem
cách dùng. JEI và MezzConfig được cài ở client. File
**Forgotten-Worlds-Optimized-1.21.11.mrpack** tải riêng có cùng nội dung với gói
nhúng trong launcher và được ghi hash trong **SHA256SUMS**.

## Sửa cập nhật launcher trên Windows

Khi launcher nằm trong thư mục cần quyền quản trị, bộ cập nhật dùng bộ cài Windows
đúng phiên bản, kiểm SHA-256 rồi mở UAC. Hủy UAC thì launcher vẫn chạy. Bản cài vào
thư mục ghi được tiếp tục dùng cập nhật zip.
