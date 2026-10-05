Sửa lỗi **"thất bại sau 4 lần thử: không gọi được https://cdn.modrinth.com/..."** trên Windows.

## Triệu chứng

Trên một số máy Windows 10 (nhất là máy lâu không cập nhật Windows), bấm **Tạo bản chơi** ở
một modpack hoặc tải mod từ Modrinth thì hiện thông báo đỏ "thất bại sau 4 lần thử: không gọi
được https://cdn.modrinth.com/data/...". Mở trình duyệt hay chạy `curl.exe` tới cùng địa chỉ
thì vẫn vào được bình thường.

## Nguyên nhân

Launcher kiểm chứng chỉ HTTPS bằng thư viện `ssl` của Python, thứ chỉ tin các chứng chỉ gốc
**đang nằm sẵn** trong kho của Windows. Nhưng Windows không giữ đủ chứng chỉ gốc trong kho: nó
tải thêm từ Windows Update đúng lúc cần — và chỉ khi chính Windows (Schannel) kiểm chứng chỉ,
như trình duyệt hay `curl.exe`. Máy thiếu chứng chỉ gốc mà CDN của Modrinth đang dùng thì
launcher từ chối kết nối, còn curl thì không.

## Sửa

Launcher giờ giao việc kiểm chứng chỉ cho **chính hệ điều hành** (qua thư viện `truststore`,
thứ pip cũng dùng): Schannel trên Windows, Security.framework trên macOS, kho chứng chỉ hệ thống
trên Linux. Launcher kết nối được ở đâu thì trình duyệt và curl kết nối được ở đó. Việc kiểm
vẫn đầy đủ như trước — chứng chỉ sai hay sai tên máy vẫn bị từ chối.
