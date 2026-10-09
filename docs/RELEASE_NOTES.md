# Nostalgia 1.2.0rc18 — Modpack của bạn, mang đi dễ dàng hơn

Chia sẻ đúng bộ mod, mang bản chơi sang máy khác và dọn những thế giới không còn dùng. Bản cập nhật này sửa lỗi nhận diện Forge khi chơi chung, thay thao tác sao lưu bằng xuất modpack và bổ sung xóa vĩnh viễn ngay trong launcher.

## Forge: chơi được thì chia sẻ đúng phiên bản

Profile Forge hiện đại khai `fmlloader` thay vì thư viện tên `forge`. Launcher đã nhận đúng phiên bản từ profile chính thức, khắc phục thông báo **“Không tìm thấy phiên bản loader. Hãy cài lại loader trước khi chia sẻ”** với bộ cài hợp lệ.

- Host và đồng bộ modpack dùng đúng Minecraft và phiên bản Forge đã cài.
- Xuất modpack và quét sửa mod dùng cùng bộ nhận diện đã sửa.
- Giữ hỗ trợ Fabric, Quilt, Forge cũ và NeoForge; không nhầm phiên bản thư viện FML độc lập của NeoForge thành phiên bản loader.

## Từ Sao lưu sang Xuất modpack

Vào **Bản chơi → Xuất modpack**, chọn bản chơi, định dạng và nơi lưu:

- **MRPACK** theo định dạng Modrinth hoặc **ZIP** theo định dạng modpack CurseForge; có thể nhập lại qua **Nhập bản chơi**.
- Đóng gói các file hiện có, gồm mod tự thêm, mods đang bật hoặc tắt, resourcepack, shader, cấu hình và script. Giữ đúng Minecraft và loader.
- Bật **Đóng gói cả thế giới** nếu muốn mang theo thư mục `saves`. Mặc định giữ thế giới riêng trên máy.
- Xuất chạy ở nền và giữ bản chơi gốc. Nếu ghi file thất bại hoặc nội dung thay đổi trong lúc xuất, giữ file đích cũ và báo lỗi thay vì để lại gói nửa vời.
- Bản sao lưu/thùng rác từ phiên bản cũ vẫn có mục **Khôi phục dữ liệu cũ**, kèm hướng dẫn GIF mới.

## Xóa hẳn, rõ ràng trước khi xác nhận

Trong **Quản lý bản chơi → Xuất & dữ liệu → Xóa vĩnh viễn**, launcher xác nhận trước khi xóa mods, cấu hình và thế giới thuộc bản chơi. Không chuyển dữ liệu sang thùng rác.

Nếu dùng thư mục game riêng, bật **Xóa cả thư mục game riêng** để xóa cả dữ liệu tại đường dẫn được hiển thị. Launcher chặn đường dẫn chứa kho chung hoặc trùng với bản chơi khác. File modpack đã xuất ở bên ngoài được giữ lại. Có thêm nút xóa hẳn từng bản chơi trong thùng rác cũ.

**Xóa vĩnh viễn không thể hoàn tác. Hãy xuất modpack kèm thế giới trước nếu còn muốn giữ dữ liệu.**

## Cập nhật và bộ cài

Giữ cách cập nhật quen thuộc: launcher báo bản mới, chỉ tải và cài khi bạn bấm **Cập nhật ngay**. Gói cập nhật được kiểm SHA-256 trước khi áp dụng.

- **Windows x64:** bộ cài `setup.exe` và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

Google và Premium dùng dịch vụ thật; bản phát hành không mở Ultimate TEST. Chỉ đính kèm bộ cài, gói portable/cập nhật và `SHA256SUMS`.
