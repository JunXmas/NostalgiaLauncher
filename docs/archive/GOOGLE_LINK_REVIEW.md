# Bước liên kết Google sau đăng nhập Minecraft

Microsoft/Ely.by đăng nhập thành công sẽ hiện **Liên kết Google với Nostalgia**,
với nút Google và **Để sau · Vào launcher**. Google đã đăng nhập thì vào thẳng
launcher. Tài khoản ngoại tuyến và thao tác khám phá trước giữ luồng hiện có.

Lời mời chỉ được kích hoạt bởi tín hiệu đăng nhập thành công, không chen vào
khởi động của tài khoản Minecraft đã lưu. Liên kết thành công hoặc chọn Để sau
lưu lựa chọn trên máy trong `config/onboarding.json`; đăng nhập Minecraft lần
sau không hỏi lại. Liên kết sau vẫn có ở mục Bạn bè. Cờ này chỉ điều khiển UI,
không chứng minh đã đăng nhập Google và không cấp Plus/quyền server.

Trong lúc chờ có Mở lại Google và Để sau. Bỏ qua sẽ hủy polling, bỏ kết quả
khởi tạo đến muộn và giữ tài khoản Minecraft. Lỗi Google cho phép thử lại hoặc
bỏ qua; dịch vụ chưa cấu hình vẫn có thể Để sau. Chỉ snapshot tài khoản đã xác
thực mới hoàn tất bước liên kết. Đăng nhập miễn phí không tự nhận quyền Plus.

Khung mica có logo Google, animation mở nhẹ và chế độ giảm chuyển động. Hai nút
chính cố định ở chân khung; nội dung mô tả cuộn riêng khi cửa sổ hẹp/chữ lớn.

Kiểm tra: 41 bài Qt/OpenGL và kiến trúc/quy ước đạt, gồm Microsoft, Ely.by,
lưu Để sau, Google đã liên kết, chờ snapshot, lỗi/thử lại/hủy, phản hồi đến muộn,
dịch vụ chưa cấu hình, màn hình nhỏ 100/150%, quyền miễn phí và các luồng cũ.
Ruff, format, mypy (552 file) và diff đạt. Các test xác thực dùng fixture;
không xác thực tài khoản Google/Microsoft/Ely.by thật hoặc triển khai backend.

7 ảnh chụp Qt/OpenGL để review tại `/workspace/artifacts/nostalgia-google-link-flow`,
gồm 1440×900 và 1024×600 với chữ 150%. Nhật ký QML khi capture rỗng. Preview không
đưa vào release, không build bộ cài hoặc sửa draft.
