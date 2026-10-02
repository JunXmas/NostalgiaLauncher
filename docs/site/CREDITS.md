# Nguồn ảnh của trang tải

## `hero.webp`

Ảnh chụp trong game, **do chính dự án này chụp**, không lấy từ đâu về.

| Mục | Giá trị |
|---|---|
| Nguồn | Chụp từ chính Nostalgia Launcher, bản chơi `fabric-loader-0.19.3-1.21.11` |
| Cảnh | Thế giới savanna, chế độ spectator, `/time set 23000` (bình minh), `/weather clear` |
| Cách chụp | Headless: Xvfb `:99` 1920×1080, `LIBGL_ALWAYS_SOFTWARE=1`, F1 tắt toàn bộ HUD, `import -window root` |
| Hậu kỳ | Lật ngang (mặt trời sang phải, trời tối sang trái nơi đặt chữ), WEBP q78 method 6 |
| Kích thước | 1920×1080, 145 484 byte |

Vì sao không dùng ảnh có sẵn: các ảnh trong `screenshots/` của máy chủ dự án có bảng điểm
máy chủ, tên người chơi và ảnh cá nhân dán góc — không đưa lên trang công khai được. Vì sao
không dùng key art của Mojang: giấy phép phi thương mại chỉ cho dùng minh hoạ **trong
launcher** (xem `src/nostalgia/ui/qml/assets/keyart/CREDITS.md`), còn đây là trang web.

Nội dung trong khung hình là thế giới và texture của **Mojang Studios / Microsoft**; ảnh
chụp màn hình game dùng để minh hoạ một công cụ phi thương mại cho chính game đó. Dự án
không liên kết với Mojang hoặc Microsoft — câu này cũng in ở chân trang.

## `logo.webp` và `favicon.png`

Cùng một hình với icon ứng dụng, **không phải SVG vẽ lại cho giống**. Người dùng nối trang
web với app vừa cài bằng đúng cái hình đó; hai hình na ná nhau là lý do để họ nghi file vừa
tải.

| File | Nguồn gốc | Xử lý |
|---|---|---|
| `logo.webp` | `src/nostalgia/ui/qml/assets/logo.png` (256×256 RGBA, cũng là logo trong `Sidebar.qml`) | Co về 128×128 LANCZOS, WEBP q88 method 6 — 12 550 byte, nhỏ hơn PNG cùng cỡ (26 447 byte) |
| `favicon.png` | `packaging/icons/nostalgia-32.png` | Chép nguyên byte, không xử lý gì |

`favicon.png` là bản **chép**, nên nó trôi im lặng: đổi icon ứng dụng mà quên chép lại thì
tab trình duyệt vẫn hiện một hình hợp lệ, chỉ là khác hình trên thanh tác vụ.
`tests/test_site.py::test_the_favicon_is_byte_for_byte_the_icon_the_installed_app_uses` so
theo byte để chặn chuyện đó.

Logo khối lá là tác phẩm của **jun** (gốc `packaging/icons/nostalgia-source.png`), theo
giấy phép của kho — AGPL-3.0.

## `../showcase/*.jpg`

Ảnh chụp giao diện của chính launcher này. Trong đó `home.jpg`, `create-instance.jpg` và
`library.jpg` có key art Minecraft hiện bên trong cửa sổ app — nguồn và giấy phép của phần
key art ấy ghi ở `src/nostalgia/ui/qml/assets/keyart/CREDITS.md`.
