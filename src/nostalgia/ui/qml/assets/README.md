# Ảnh dùng trong giao diện

`hero.jpg` — ảnh làng Minecraft do chủ dự án cung cấp (tạo bằng công cụ sinh ảnh rồi upscale,
gốc 2528×1686), giữ **nguyên độ phân giải** và làm nét thích nghi
(`convert -adaptive-sharpen 0x1.8 -unsharp 0x1.0+1.0+0.02 -quality 90`; bản 1800 px trước đây
bị chê mờ), **không cắt**: ảnh làm nền cho toàn vùng nội dung của trang chủ, được phủ kiểu
"cover" nên hai bên có thể bị xén tuỳ tỉ lệ cửa sổ. `Image` vẽ với `mipmap: true` vì ảnh luôn
bị thu nhỏ.

Không còn thẻ nào neo vào công trình trong ảnh, nên đổi ảnh không phải đo lại toạ độ — chỉ cần
nó vẫn đủ tối ở đáy để dải bản chơi đọc được.

`discord.png` — logo Discord chính hiệu, do chủ dự án cung cấp
(`discord-color-icon.webp` 512×512). Cắt viền trong suốt, đệm về ô vuông, thu còn 88 px
(4× ô icon 22 px, đủ cho mipmap). Giữ NGUYÊN màu lam của Discord: logo đổi màu thì mất tác
dụng nhận diện, nên đây là thứ duy nhất ở thanh bên nằm ngoài bảng màu Nostalgia.
Nhãn hiệu của Discord Inc.; dùng để trỏ tới chính máy chủ Discord của dự án.
