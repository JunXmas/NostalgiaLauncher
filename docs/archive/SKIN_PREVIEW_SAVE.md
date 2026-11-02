# Skin và cape: xem trước rồi lưu

Bản sửa trên nhánh `fix/account-menu-visibility`, chưa có trong bộ cài rc13.

## Hành vi

- Nhập PNG và chọn thẻ skin chỉ chỉnh bản xem trước, không đổi tài khoản.
- Công tắc Classic/Slim đổi hình học tay 4/3 pixel ngay trên nhân vật.
- Thẻ cape dùng nhân vật mặc áo choàng, nhìn từ sau; thử cape tự xoay khung chính.
- Lưu dùng tài khoản được chốt lúc bấm nút. Bản đang chỉnh được giữ riêng cho từng
  tài khoản, không lẫn khi đổi tài khoản hoặc tài khoản trùng tên.
- Hủy trở về diện mạo đã lưu. Chọn lại cùng texture và dáng tay không upload thừa.
- Skin lưu được nhưng cape thất bại thì giữ cape chờ lưu và chỉ thử lại phần đó.

## Dịch vụ

Microsoft giữ luồng làm mới vé và upload Mojang với `variant=classic|slim`.
Cape chỉ chọn từ danh sách đã sở hữu, mặc/gỡ qua API Mojang.

Ely.by giữ phiên web, upload vào kho rồi mặc skin. Khi dáng tay của skin trên Ely.by
khác lựa chọn, launcher đọc form sửa skin do Ely.by cung cấp và gửi đúng action/method
của form. Action khác origin, form không đọc được hoặc dịch vụ chưa xác nhận dáng tay
sẽ dừng trước bước mặc skin. Không tự coi đổi ảnh cục bộ là đổi skin trong game.
Form phụ thuộc trang Ely.by; chưa kiểm tra bằng phiên web của một người dùng thật.

Ely.by chưa có API đổi cape trong launcher; áo choàng đang dùng vẫn xem được 3D.
Không gửi thông tin đăng nhập, cookie hay file skin cho dịch vụ của launcher.

## Hiệu năng và kiểm thử

Renderer dùng hộp cape vanilla 10x16x1, UV 64x32 và xử lý độ sâu sau lưng.
Thẻ thư viện chỉ dựng thumbnail ở viewport; khung xoay dùng atlas ở worker chung.
Thumbnail hiện trước khi atlas dựng xong để phản hồi lựa chọn skin/cape sớm hơn.
Giữ giới hạn 32 frame, 8 mesh/atlas, 48 thumbnail và 64 MiB cache ảnh preview.
Không chạy vòng animation nền khi người chơi không tương tác hoặc cửa sổ bị ẩn.
Digest skin/cape cập nhật cache khi ảnh đổi dù đường dẫn file giữ nguyên.

Kiểm thử qua HTTPS cục bộ xác minh bytes skin, dáng tay, phiên Ely.by, tài khoản
trùng tên và lỗi dịch vụ. Qt/OpenGL kiểm tra công tắc, chọn/thử cape, lưu, hủy,
đổi tài khoản, lỗi một phần và làm mới ảnh. Đây là fixture, không phải xác nhận
đã đổi skin trên tài khoản Microsoft/Ely.by thật.

Kết quả lượt kiểm tra cuối: 59 kiểm tra skin/quy ước/API và 24 kiểm tra Qt/OpenGL
đều qua; Ruff và mypy sạch.
