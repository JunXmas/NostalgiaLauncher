# Host chọn modpack và tự khởi chạy — preview mã nguồn

Bấm **Mở phòng** ở Bạn bè mở cửa sổ mica chọn bản chơi/modpack đã cài. Chọn một bản chơi, xem phiên bản và số mod, rồi bấm **Host & khởi chạy**. Launcher chuẩn bị và chạy chính bản đó; không cho chọn lại một pack khác sau khi mở LAN.

Luồng đồng bộ Plus chụp mods/config/defaultconfigs/kubejs/scripts/resourcepacks/shaderpacks được phép sau khi bổ sung bản cài và Nos Client, trước khi khởi chạy game. Chỉ dùng cổng LAN báo từ stdout của game đã chọn; không chọn một Minecraft khác qua multicast. Cổng vẫn phải qua Minecraft status probe trên loopback. Với bản/mod không ghi thông báo LAN chuẩn, có lựa chọn nhập cổng thủ công.

Trong Minecraft, người chơi vẫn cần vào hoặc tạo thế giới rồi **Esc → Open to LAN → Start LAN World**. Launcher tự mở game, không tự chọn thế giới hoặc tự sửa thế giới để mở LAN. Khi relay cấp vé host, launcher tự gửi bản chụp đã chuẩn bị. Lời mời bị khóa ở cả UI và SocialBridge cho đến khi upload/commit thành công; phòng cũng khóa nhận khách trong lúc gửi. Bạn bè tải vào bản chơi mới, với cùng game/loader và file kiểm SHA-256 qua luồng guest hiện có.

Đồng bộ lỗi giữ Minecraft đang chạy và cho thử gửi lại cùng bản chụp. Hủy trước khi game chạy hủy việc chuẩn bị. Hủy sau khi game chạy chỉ dừng phòng/đồng bộ, game vẫn chơi cục bộ được. Game thoát, crash, mất relay hoặc phiên Google bị thu hồi đều dừng phòng và bỏ kết quả về muộn. Bản chụp tạm được dọn khi phiên game kết thúc.

## Trạng thái triển khai

- Chỉ cập nhật nhánh `preview/glass-review`; không đổi `main`, không tag/build installer/draft/release, không deploy backend.
- `ui/runtime.py` vẫn đặt `plus_enabled=False` và gateway thanh toán/sửa lỗi trả phí vẫn tắt. Host & khởi chạy dùng được khi dịch vụ Google đã cấu hình; tùy chọn đồng bộ Plus vẫn tạm khóa trong cấu hình phát hành.
- Google thật còn chờ Worker URL/D1 và callback OAuth đúng cấu hình. Không tuyên bố đã đăng nhập Google hoặc chơi multiplayer qua backend production thành công.
- Quyền upload Plus, vé host và quyền guest vẫn do backend kiểm; điều kiện hiển thị Qt không cấp Plus. Không đưa secret Google vào client hoặc preview.

## Ảnh xem trước

Ảnh chụp Qt/OpenGL thật, không dựng bằng công cụ tạo ảnh. Tài khoản, JVM/relay/upload trong ảnh dùng fixture kiểm thử, không kết nối dịch vụ production.

- [Chọn pack — Plus đang tạm khóa](preview/host-selection/HOST_PICKER.png)
- [Màn hình 1024×600, tỷ lệ chữ 150%](preview/host-selection/HOST_PICKER_SMALL.png)
- [Chờ LAN từ game đã chọn](preview/host-selection/HOST_WAITING_LAN.png)
- [Đang tự gửi modpack — trạng thái Plus mô phỏng](preview/host-selection/HOST_SYNCING.png)
- [Sẵn sàng mời bạn — trạng thái Plus mô phỏng](preview/host-selection/HOST_READY.png)

Ảnh đồng bộ/sẵn sàng minh họa nhánh Plus bằng fixture; không bật Plus trong bản phát hành.

## Kiểm tra

Kết quả cuối ngày 2026-10-07:

- Toàn bộ: `QT_QUICK_BACKEND=software uv run pytest -q` → **1.439 passed, 7 skipped, 1 deselected**, 293,61 giây. Không chạy test mạng production.
- Kiểm lại UI/host, Social, RoomSync, Content, lựa chọn giao diện và Select dưới Qt/OpenGL → **44 passed**, 27,53 giây.
- 5 ảnh Qt/OpenGL thật → **0 cảnh báo QML**, có SHA-256 trong thư mục ảnh.
- Ruff check/format, mypy (487 file), `uv lock --check`, kiểm kiến trúc/ranh giới API và `git diff --check` đạt.
- Lượt toàn bộ đầu có một test thư viện đọc model trước tín hiệu Qt (`1 failed, 1.438 passed`). Đã sửa test chờ model cập nhật thay vì chỉ chờ cờ worker; lượt toàn bộ cuối xanh. Không đổi mã tìm kiếm thư viện.

Bộ kiểm tra mới bao phủ chọn đúng Forge instance, Nos Client trước snapshot, file nguồn đổi sau launch, cổng stdout báo sớm, beacon khác không được dùng, Minecraft status thật trên loopback, khóa lời mời khi upload chờ/403, retry giữ nguyên snapshot, cancel/crash/logout/mất relay, pack không tồn tại/launcher bận/game đang chạy, Plus bị tạm khóa/tài khoản free, chọn bằng bàn phím và popup mica ở 1024×600 với 100%/150%.

JVM và cổng upload trong kiểm tra điều phối host được kiểm soát bằng fixture. Không thay thế kiểm thử chơi một modpack thật qua dịch vụ production giữa hai máy.
