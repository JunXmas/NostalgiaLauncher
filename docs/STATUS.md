# Hiện trạng

Ghi đúng những gì bản trên nhánh `main` đang làm, kèm chỗ trong mã để tự kiểm. Báo cáo
review/preview/validation cũ đã dời vào [`archive/`](archive/); chúng chụp lại từng thời điểm,
không phải hiện trạng.

Cập nhật: 2026-11-02 (nhánh `feat/plus-v2`).

## Giao diện

- Chỉ còn một giao diện: `src/nostalgia/ui/qml/app/Main.qml`, dựng bởi
  `src/nostalgia/ui/window.py` (`open_window`). Điểm vào duy nhất: `nostalgia-ui` →
  `nostalgia.ui.runtime:main`.
- Giao diện cũ (classic) đã gỡ. File cấu hình còn `"interface_style": "classic"` vẫn đọc trơn
  và mở giao diện mới; lần lưu sau thì trường cũ biến mất
  (`tests/settings/test_settings_store.py::test_old_classic_interface_choice_is_read_silently`).
- Bấm Chơi (thẻ bản chơi, nút Chơi ở trang chủ) mở cửa sổ chọn: tab Chơi đơn (lưới thế giới, ảnh
  `icon.png`) và Chơi mạng (server trong `servers.dat`, không ping); bấm thẻ là vào thẳng qua
  `--quickPlaySingleplayer` / `--quickPlayMultiplayer` (đời 1.6-1.19: `--server/--port`).
  Bản chơi không có gì để chọn thì mở game luôn (`app/PlayChoiceDialog.qml`,
  `bridge.loadPlayChoices` ở `src/nostalgia/ui/instance_bridge.py`).
- Giờ chơi trên thẻ bản chơi chưa có trên giao diện mới; cầu nối vẫn còn (`playtimeText` /
  `launchCount`) cho hồ sơ sau này.

### Nostalgia+ và thanh toán: ĐANG BẬT THẬT

- Một sản phẩm, hai giá: 79.000đ/năm (`plus-year-v3`) và 199.000đ mua đứt (`plus-lifetime-v2`).
  Offer id và giá chỉ nằm ở `src/nostalgia/payment/catalog.py`; giá tính tiền vẫn là giá
  máy chủ báo. Worker còn bảng giá cũ từ chối id mới thì launcher dùng offer mặc định của
  máy chủ (`src/nostalgia/ui/payment_plan.py` `fetch_offer`, log warning).
- Quyền lợi: cosmetic hồ sơ cao cấp + màu hồ sơ, huy hiệu, tải bản launcher thử sớm. Một cờ
  `socialBridge.account.plus` mở cả ba. Không khoá tính năng chơi nào; host server trên máy
  mình miễn phí (cổng quyền server đã gỡ khỏi launcher).
- Người mua bốn gói cũ (`plus-month-v1`, `plus-half-year-v1`, `plus-year-v2`,
  `plus-lifetime-v1`) giữ quyền và hạn, nhãn "Người ủng hộ sớm"; gói mua đứt cũ vẫn là mua
  đứt (`tests/social/test_early_supporter.py`).
- Bật bán theo cờ riêng `plus_enabled` trong `src/nostalgia/social/service-defaults.json`
  (đè bằng `NOSTALGIA_PLUS_ENABLED=0|1`), không suy từ `account_url`.
- Đăng nhập Google xong là nối `HttpPaymentGateway` thật (`POST /v1/plus/orders`). Đơn tạo
  ra là đơn thật, duyệt tay ở Worker `nostalgia-payment-admin`.
- Thứ tự ưu tiên địa chỉ dịch vụ (`src/nostalgia/social/configuration.py`,
  `read_configuration`): biến môi trường `NOSTALGIA_ACCOUNT_URL` / `NOSTALGIA_ROOM_SYNC_URL`
  > `services.json` của người dùng > `service-defaults.json` cài sẵn.
- Công cụ draft `ReviewPanel.qml` bị lọc khỏi gói release (`packaging/nostalgia-ui.spec`,
  kiểm ở `packaging/verify-build-flavor.py`).

## Slide quảng cáo trang chủ

- Feed `promotions.json` ở gốc kho, tải qua `raw.githubusercontent.com` lúc mở launcher
  (`src/nostalgia/content/promotions.py`). Sửa file trên `main` là mọi launcher thấy.
- Loại `server` (`address: host:port`, vào bằng bản chơi đang chọn) và `link` (`url` https,
  mở trình duyệt). Field lạ bỏ qua, `kind` lạ bỏ riêng slide đó; chỉ tăng `schema` khi đổi
  không tương thích. `starts_at`/`ends_at` giây Unix, 0 là không giới hạn.
- Ảnh chỉ từ `raw.githubusercontent.com`, PNG/JPEG ≤ 1 MB, ≤ 2560 px. Offline/hỏng dùng bản
  đệm ở `<data>/updates/promotions/`; không có đệm thì ẩn slide.
- Forgotten Worlds đã gỡ khỏi launcher. `modpacks/forgotten-worlds.json` vẫn ở kho để
  launcher cũ không lỗi; bản chơi FW người dùng đã tạo chạy như bản chơi thường.

# Chơi chung

- **Relay dữ liệu bị tắt cứng.** `src/nostalgia/multiplayer/room_network.py:90`
  `self._relay_enabled = False`; không chỗ nào bật lại. Không có P2P thì
  `require_room_transport` (cùng file, dòng 98–107) báo "relay dữ liệu đã tắt".
  Đồng bộ modpack cũng chỉ đi P2P: `src/nostalgia/multiplayer/sync_gateway.py:96-98`
  và `:147`.
- **P2P không có TURN.** ICE chỉ có STUN: `src/nostalgia/multiplayer/peer_connection.py:39`
  (`stun:stun.cloudflare.com:3478`) và danh sách dự phòng ở
  `src/nostalgia/multiplayer/peer_stun.py:17-18`. Không STUN nào trả lời thì chỉ thử ứng viên
  cục bộ (`peer_stun.py:117-120`). Hai máy sau NAT đối xứng / CGNAT sẽ không nối được.
- **Đồng bộ phòng cần backend Plus chưa deploy.** `src/nostalgia/ui/runtime.py:112`: chỉ nối
  `HttpRoomSyncGateway` khi đã đăng nhập và có `room_sync_url`
  (`service-defaults.json:3`). Phía máy chủ (`/v1/rooms/{id}/sync`, cấp vé Plus) nằm ở kho
  backend riêng và chưa deploy; xem `archive/MULTIPLAYER_PLUS_SYNC_PREVIEW.md` mục "Cấu hình
  còn thiếu để dùng thật". Khi relay chưa cấp vé, `RoomSyncCard.qml:39` nói thẳng điều đó.
- Mô hình đe doạ và 10 luật bảo mật: [MULTIPLAYER_SECURITY.md](MULTIPLAYER_SECURITY.md).

## Ghi log

- Lỗi làm chết cả một bước mạng phải để lại `warning`: `peer_host.py` (`_serve`),
  `room_network.py` (`_watch_host`, `enable_direct_host`). Một interface mạng lẻ lỗi trong khi
  cái khác chạy được thì `debug` (`lan.py`, join multicast và phát beacon), hỏng hết mới
  `warning`. Gác bởi `tests/multiplayer/test_swallowed_errors_logged.py`.
