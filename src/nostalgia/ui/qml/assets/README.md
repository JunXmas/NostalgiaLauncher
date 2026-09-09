# Ảnh dùng trong giao diện

`hero.jpg` — ảnh làng Minecraft do chủ dự án cung cấp (tạo bằng công cụ sinh ảnh rồi upscale,
gốc 2528×1686), giữ **nguyên độ phân giải** và làm nét thích nghi
(`convert -adaptive-sharpen 0x1.8 -unsharp 0x1.0+1.0+0.02 -quality 90`; bản 1800 px trước đây
bị chê mờ), **không cắt**: ảnh làm nền cho toàn vùng nội dung của trang chủ, được phủ kiểu
"cover" nên hai bên có thể bị xén tuỳ tỉ lệ cửa sổ. `Image` vẽ với `mipmap: true` vì ảnh luôn
bị thu nhỏ.

Toạ độ công trình trong `HeroPanel.qml` là phần trăm trên ảnh gốc; `HeroPanel` tự ánh xạ qua
phép cắt cover. Đổi ảnh là phải đo lại.
