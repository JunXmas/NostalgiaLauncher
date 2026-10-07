# Giao diện và chuyển động · draft 1.2.0rc7

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

Tham khảo bản mã JavaScript của https://skewclient.store đã lưu ngày 2026-10-06.
Lần truy cập lại ngày 2026-10-07 trong môi trường này trả HTTP 403.
Trang dùng Lenis 1.3.26 với `lerp: 0.1`, `duration: 1.5`, `smoothWheel: true`.
Khi có duration/easing, Lenis ưu tiên easing theo thời gian. Easing là exponential-out.

Launcher dùng FrameAnimation của Qt: mỗi frame tiến về vị trí đích với hệ số
`1 - exp(-(10 * ln(2) / 1.5) * dt)`. Đây là xấp xỉ liên tục của cùng độ hãm,
giữ trọng lượng của chuyển động khi nhịp render thay đổi. Mỗi nấc chuột dịch đích
92 px; nhiều nấc tích luỹ, đảo hướng không nhảy vị trí. Chặn ở đầu/cuối nội dung.
Kéo nội dung bám con trỏ; thả ra chuyển vận tốc kéo thành quãng trôi được hãm
bằng cùng đường cong. Controller đo chuyển động lúc kéo để vẫn có quán tính khi Qt
không phát native fling; giữ con trỏ đứng yên trước khi thả thì dừng. Nấc chuột và pixel delta đều được làm mượt. Kéo thanh cuộn
dừng quán tính để đặt vị trí chính xác. Giảm chuyển động bỏ phần trôi.

Áp dụng cho Home, thư viện, Đã cài, quản lý instance, popup, form tạo bản chơi và
Cài đặt, danh sách phiên bản/loader, tài khoản, log và lưới/danh sách nâng cao của
thư viện. ListView/GridView giữ cơ chế dựng mục trong vùng nhìn của Qt; dropdown
nhỏ vẫn dùng cuộn Qt thông thường.
Chưa đo thực tế trên màn hình 120/144 Hz hoặc mọi model chuột/trackpad Windows.

## Việc cần chủ dự án thử trên máy thật

- Cảm giác cuộn nhanh/chậm, đảo hướng, kéo scrollbar, trackpad và Giảm chuyển động.
- Form/cửa sổ ở 1024×600 và chữ 150%; ghim, tìm nhóm, lưu RAM và quản lý mod.
- Độ mờ mica trên GPU máy đích; chế độ software có nền thay thế và không blur shader.
- Không đồng nhất hoá launcher bằng cách tăng animation mọi nơi: chữ, form và hành
  động chính cần đọc rõ trước; animation chỉ giúp theo dõi thay đổi và phản hồi thao tác.

## Mica và skin 3D ở rc6

Popup đăng nhập/cài pack lấy scene bên ngoài popup, bỏ màu nền đặc và animation scale
để sourceRect kính khớp nội dung phía sau. Thẻ đăng nhập đầu tiên, mã Microsoft và
popup thêm tài khoản cùng dùng mica. Chế độ software có nền thay thế, không blur GPU.

Skin dùng sáu hộp và lớp ngoài đúng UV Steve/Alex; chuẩn hoá skin 64x32 và skin HD.
Một worker dựng thumbnail và atlas 72 hướng (bước 5 độ). Khi kéo/phím đổi góc, QML
chỉ dịch atlas đã nạp; không giải mã PNG hoặc gọi Python render theo từng góc.
Không có timer xoay lúc rảnh. Thẻ ngoài vùng nhìn không nạp preview; ẩn/thu nhỏ cửa
sổ bỏ nguồn ảnh. Kho skin dùng cuộn quán tính và cỡ chữ của launcher.

Atlas 1536x1536: 9 MiB RGBA cho nhân vật đang tương tác; thẻ kho dùng thumbnail nhỏ.
Cache CPU tối đa 32 frame (4 MiB) và tám mesh, cache đĩa giới hạn 64 MiB, map preview
48 thumbnail/tám atlas. Không thêm QtQuick3D/Addons hoặc engine web. Giới hạn này
không phải toàn bộ RAM launcher/GPU driver. Kết quả benchmark cục bộ ở RC6_VALIDATION.md.

## Đã cài và ô phiên bản ở rc7

Tên/phiên bản được đọc từ Fabric, Quilt, Forge, NeoForge hoặc mcmod.info ở worker.
Cache mtime/size tránh giải nén lại khi bật/tắt/lọc; hash đối chiếu nguồn mới cấp
ID dự án. Watcher thư mục có debounce 160 ms cập nhật file thêm/xoá. Quét nền có
kết quả local trước mạng; đổi bản chơi không nhận nhầm kết quả của bản trước.

Viền focus trắng của theme cũ được tắt ở theme mới; ô phiên bản giữ viền bo góc
của chính nút khi dùng chuột hoặc bàn phím. Thẻ Optimized tự tăng chiều cao;
lưới loader giảm số cột theo cỡ chữ để mô tả/nhãn không đè lên nút ở cửa sổ nhỏ.
Giữ bảng màu và ảnh Minecraft hiện có.
