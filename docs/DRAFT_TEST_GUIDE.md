# Nostalgia 1.2.0rc8 — bản draft Ultimate TEST

Bản này dành cho chủ dự án thử, mặc định mở đầy đủ quyền **Ultimate TEST**.
Đây là GitHub draft, chưa publish; trình tự cập nhật không phân phối bản này.
Không có giao dịch ngân hàng và không cộng quyền vào tài khoản Google thật.

## Cài và bắt đầu

- Windows: tải `nostalgia-1.2.0rc8-windows-x64-setup.exe` hoặc giải nén ZIP.
- Linux: AppImage, DEB, RPM hoặc TAR.GZ/ZIP.
- macOS: chọn DMG/ZIP đúng Apple Silicon (arm64) hoặc Intel (x64).
- Kiểm tra file theo SHA256SUMS. Đóng launcher cũ trước khi mở bản thử.
- Đăng nhập tài khoản Minecraft như thường; cũng có thể bỏ qua đăng nhập để xem UI.
- Góc trên bên phải có **Ultimate TEST · Công cụ Draft**. Mỗi lần chạy mặc định Ultimate.

Gói thử dùng thư mục dữ liệu launcher hiện có. Nên sao lưu bản chơi trước khi cài/gỡ
mod hoặc chỉnh server. Hồ sơ TEST lưu riêng tại `config/draft-review/profile.json`;
không sửa credential Google hay tài khoản Minecraft.

## Những gì thử được

| Luồng | Cách thử |
| --- | --- |
| UI mới | Home, thư viện, popup phiên bản có tìm kiếm, mica, cuộn quán tính, chữ 150% và cửa sổ nhỏ. |
| Mods đã cài | Chọn modpack, xem danh sách đọc metadata JAR/cập nhật khi file thay đổi. |
| Cosmetic | Vào Bạn bè, mở hồ sơ của mình, chọn Amethyst/Grove/Eclipse và lưu. Plus vẫn chọn được một bộ trong ba. |
| Server local | Ở Bản chơi chuyển sang Server, tạo và cấu hình Paper/Purpur/Folia/Fabric/Vanilla hoặc các hybrid có trong danh mục. Plugin/mod và Java tải từ nguồn thật, EULA vẫn cần chấp thuận. Không có VPS đi kèm. |
| Quyền từng gói | Trong Công cụ Draft chọn Plus/Pro/Max/Ultimate. Plus không host server; Pro trở lên có. Dừng server trước khi đổi gói. |
| Sửa mod | Quét và lập phương án cho mod trùng ID, sai loader hoặc xung đột đã xác minh. Chỉ áp khi toàn bộ phương án kiểm tra được; có sao lưu/hoàn tác. Lỗi thiếu phụ thuộc, sai khoảng phiên bản hoặc metadata chưa hiểu sẽ báo chưa xử lý trong planner local này. |
| Đồng bộ modpack local | Trong Công cụ Draft chọn bản chơi đã cài và bấm “Đồng bộ local · Tạo bản chơi mới”. Kiểm hash và cài đúng loader vào instance mới, không chép saves/log/account. Có thể cần tải Minecraft/loader. Đây không phải gửi pack giữa hai máy. |
| Bạn bè/chat | Misa/Huy/Minh mang nhãn TEST, trả lời mô phỏng để xem bố cục, avatar và hồ sơ. Không có lời mời thật gửi đi. |
| Thanh toán | Xem các gói 29k/69k/109k/209k. QR chỉ mã mô phỏng, không có tài khoản ngân hàng hoặc checkout URL. “Tôi đã chuyển khoản” không tự xác nhận; Màn hình QR TEST có nút mô phỏng thành công riêng. |

## Google và chơi chung online

Workspace chưa có URL HTTPS backend tài khoản/relay hoặc quyền deploy dịch vụ.
Phiên Ultimate TEST là local, không giả vờ đăng nhập Google. Lời mời, chat thật và
đồng bộ nhiều máy chưa thể kiểm tra trong gói này. Core đăng nhập Minecraft
Microsoft/Ely.by, đổi skin, cài game và multiplayer hiện có vẫn dùng luồng thật;
chưa kiểm thử game/LAN trên nhiều máy trong môi trường build.

Build thường và wheel không nhập/đóng gói `nostalgia_draft`; backend production vẫn
kiểm quyền riêng và Plus vẫn tạm khóa. Không dùng chế độ review để phát hành công khai.
Google thật cần thiết lập theo [GOOGLE_SETUP.md](GOOGLE_SETUP.md).

## Gửi lỗi

Gửi hệ điều hành, kích thước cửa sổ/cỡ chữ, thao tác trước lỗi và log launcher.
Với lỗi cài modpack/server, ghi rõ tên pack, Minecraft, loader và build.
Không gửi token, cookie, secret hoặc toàn bộ thư mục tài khoản.
