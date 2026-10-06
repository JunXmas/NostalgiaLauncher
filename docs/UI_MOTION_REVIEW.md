# Giao diện và chuyển động · draft 1.2.0rc4

Giữ bảng màu hiện tại: nền xám lạnh, accent theo trang và màu thương hiệu xanh.
Mục tiêu là giảm sự rời rạc giữa các màn hình, đưa thao tác chính về cùng vị trí,
và tạo phản hồi dễ nhận thấy khi người chơi tương tác.

## Những vấn đề đã sửa

- Đã cài từng mở cả trang thư viện cũ. Nay có trang riêng trong thư viện mới;
  bộ lọc nâng cao cũng mở popup mới, không đổi toàn bộ giao diện.
- Sửa bản chơi từng dồn mọi trường và hành động vào một cột. Nay chia Tổng quan,
  Nội dung đã cài, Hiệu năng, Sao lưu & dữ liệu. Lưu và mở thư mục ở footer;
  thao tác xoá ở nhóm dữ liệu và hỏi xác nhận trước khi thực hiện.
- Bộ điều khiển dùng chung chuyển sang góc mềm và nền theo palette của launcher
  khi được dùng trong giao diện mới. Bản classic phục vụ tương thích vẫn giữ kiểu cũ.
- Sidebar mới vô hiệu hoá xoay block. Nay hover/focus kích hoạt lại cơ chế xoay,
  hãm và trả về mặt ban đầu; vẫn dùng model/texture Minecraft gốc.
- Tiêu đề dùng Manrope Regular/SemiBold/Bold, phần đọc dùng Inter. Font được
  đóng kèm, kiểm glyph tiếng Việt bằng Qt, có giấy phép SIL OFL đi cùng.
- Trang trượt nhẹ và mờ vào; popup mờ mở/đóng; nút co nhẹ khi nhấn, thẻ phản hồi
  hover, thanh đánh dấu trang di chuyển. Tắt chuyển động theo thiết lập hệ thống UI.

## Cuộn tham khảo Skew

Đọc mã JavaScript được phục vụ tại https://skewclient.store ngày 2026-10-06.
Trang dùng Lenis 1.3.26 với `lerp: 0.1`, `duration: 1.5`, `smoothWheel: true`.
Khi có duration/easing, Lenis ưu tiên easing theo thời gian. Easing là exponential-out.

Launcher dùng FrameAnimation của Qt: mỗi frame tiến về vị trí đích với hệ số
`1 - exp(-(10 * ln(2) / 1.5) * dt)`. Đây là xấp xỉ liên tục của cùng độ hãm,
giữ trọng lượng của chuyển động khi nhịp render thay đổi. Mỗi nấc chuột dịch đích
92 px; nhiều nấc tích luỹ, đảo hướng không nhảy vị trí. Chặn ở đầu/cuối nội dung.
Kéo thanh cuộn hoặc kéo trực tiếp dừng animation. Pixel delta của trackpad đã có
quán tính hệ điều hành nên áp dụng trực tiếp; không chồng thêm một lớp quán tính.

Áp dụng cho Home, thư viện, Đã cài, quản lý instance, popup, form tạo bản chơi và
Cài đặt. Danh sách log/skin và dropdown vẫn dùng điều khiển danh sách Qt của chúng.
Chưa đo thực tế trên màn hình 120/144 Hz hoặc mọi model chuột/trackpad Windows.

## Việc cần chủ dự án thử trên máy thật

- Cảm giác cuộn nhanh/chậm, đảo hướng, kéo scrollbar, trackpad và Giảm chuyển động.
- Form/cửa sổ ở 1024×600 và chữ 150%; ghim, tìm nhóm, lưu RAM và quản lý mod.
- Độ mờ mica trên GPU máy đích; chế độ software có nền thay thế và không blur shader.
- Không đồng nhất hoá launcher bằng cách tăng animation mọi nơi: chữ, form và hành
  động chính cần đọc rõ trước; animation chỉ giúp theo dõi thay đổi và phản hồi thao tác.
