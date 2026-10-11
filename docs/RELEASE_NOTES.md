# Nostalgia 1.2.0rc29 — Một phòng chơi, những người bạn

Mời bạn vào phòng trước, chuẩn bị modpack cùng nhau, rồi mở world. Bản này chuyển dữ liệu chơi chung sang **P2P mã hóa**, giúp hai máy trao đổi trực tiếp và giảm tải cho dịch vụ của launcher.

## Tạo phòng, mời bạn, cùng chơi

1. Vào **Bạn bè → Chơi chung**, chọn bản chơi và bấm **Tạo phòng**.
2. Mời bạn ngay trong bảng phòng. Nếu chia sẻ modpack, người nhận xem và chọn nội dung cần đồng bộ trước khi chơi.
3. Host khởi chạy Minecraft, vào world rồi chọn **Esc → Open to LAN → Start LAN World**. Launcher tự nhận cổng LAN.
4. Khách chờ kết nối và nội dung sẵn sàng, rồi bấm **Khởi chạy & vào world**. Giữ launcher mở trong lúc chơi.

Tìm bạn theo tên ngay trong danh sách, kể cả khi gõ không dấu. Danh sách dài chỉ dựng các ô gần màn hình. Chat thu gọn mặc định; mời chơi không cần mở cuộc trò chuyện.

## Kết nối trực tiếp, truyền nội dung có kiểm tra

- Dữ liệu game và file mod/resourcepack custom được chuyển qua WebRTC DataChannel với mã hóa DTLS. Thông tin thương lượng P2P được mã hóa AES-GCM và gửi qua HTTPS/WSS.
- Dịch vụ launcher giữ phòng chờ, lời mời, manifest và kiểm tra quyền. Relay truyền dữ liệu đã tắt; khi P2P không kết nối được, launcher báo lỗi rõ ràng.
- Host có Plus có thể chia sẻ modpack cho bạn được mời, kể cả khách miễn phí. Quyền chia sẻ được kiểm tra ở máy chủ.
- Người nhận chọn nội dung trước khi cài. File được kiểm SHA-256 và kích thước; mod từ nguồn công khai tiếp tục tải qua nhà cung cấp. Chỉ nhận mod custom từ người bạn tin tưởng vì chúng có thể chạy mã trên máy.

**Cả host và khách cần cập nhật lên bản này.** Bản cũ dùng relay sẽ không chơi chung được. P2P có thể không hoạt động trên mạng chặn UDP hoặc một số kiểu NAT/CGNAT; hiện không có relay dự phòng. Người trong phòng có thể biết địa chỉ IP của nhau.

## Cùng kiểm thử trên mạng thực tế

Đường truyền mã hóa và đồng bộ file đã được kiểm thử tự động trên máy cục bộ. Kết nối giữa nhiều nhà mạng và CGNAT vẫn cần người dùng thử thực tế. Nếu gặp lỗi, gửi phiên bản launcher, Minecraft/loader, hệ điều hành hai máy, trạng thái P2P và thông báo lỗi. Không gửi mã phòng, khóa phiên hoặc thông tin đăng nhập.

## Tải và cập nhật

- **Windows x64:** `setup.exe` và ZIP portable/cập nhật.
- **Linux x64:** `.deb` cho Linux Mint/Ubuntu/Debian, `.rpm`, AppImage, `.tar.gz` và ZIP cập nhật.
- **macOS:** DMG và ZIP riêng cho Apple Silicon và Intel.

Launcher giữ cơ chế cập nhật hiện có: thông báo bản mới, tải và cài khi bạn chọn cập nhật; macOS mở trang tải. Gói được kiểm SHA-256 trước khi áp dụng. Google và Premium dùng dịch vụ thật; bản này không mở Ultimate TEST. File đính kèm chỉ gồm bộ cài, gói portable/cập nhật và `SHA256SUMS`.
