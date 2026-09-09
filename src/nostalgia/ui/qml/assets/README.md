# Ảnh dùng trong giao diện

`hero.jpg` — ảnh làng Minecraft do chủ dự án cung cấp (tạo bằng công cụ sinh ảnh rồi upscale,
gốc 2528×1686), thu về 1800×1200, **không cắt**: ảnh làm nền cho toàn vùng nội dung của trang
chủ, được phủ kiểu "cover" nên hai bên có thể bị xén tuỳ tỉ lệ cửa sổ.

Toạ độ công trình trong `HeroPanel.qml` là phần trăm trên ảnh gốc; `HeroPanel` tự ánh xạ qua
phép cắt cover. Đổi ảnh là phải đo lại.
