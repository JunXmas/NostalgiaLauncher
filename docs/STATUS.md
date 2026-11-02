# Hiện trạng

Ghi đúng những gì bản trên nhánh `main` đang làm, kèm chỗ trong mã để tự kiểm. Báo cáo
review/preview/validation cũ đã dời vào [`archive/`](archive/); chúng chụp lại từng thời điểm,
không phải hiện trạng.

Cập nhật: 2026-11-02 (nhánh `chore/cleanup`).

## Giao diện

- Chỉ còn một giao diện: `src/nostalgia/ui/qml/app/Main.qml`, dựng bởi
  `src/nostalgia/ui/window.py` (`open_window`). Điểm vào duy nhất: `nostalgia-ui` →
  `nostalgia.ui.runtime:main`.
- Giao diện cũ (classic) đã gỡ. File cấu hình còn `"interface_style": "classic"` vẫn đọc trơn
  và mở giao diện mới; lần lưu sau thì trường cũ biến mất
  (`tests/settings/test_settings_store.py::test_old_classic_interface_choice_is_read_silently`).
- Ô CHƠI TIẾP và giờ chơi trên thẻ bản chơi chưa có trên giao diện mới. Cầu nối vẫn còn
  (`bridge.recentWorlds` / `playWorld` / `recentServers`, `playtimeText` / `launchCount` ở
  `src/nostalgia/ui/instance_bridge.py`) cho màn chọn world và hồ sơ sau này.

## Plus và thanh toán: ĐANG BẬT THẬT

- `src/nostalgia/social/service-defaults.json:2` cài sẵn
  `account_url = https://nostalgia-payment-admin.junbob.workers.dev`.
- `src/nostalgia/ui/runtime.py:47`: `plus_enabled=bool(configuration.account_url)`. Có URL cài
  sẵn là Plus bật, không có cờ riêng.
- `src/nostalgia/ui/runtime.py:94`: đăng nhập Google xong là nối `HttpPaymentGateway` thật
  (`src/nostalgia/payment/gateway.py:41` `create_order` → `POST /v1/plus/orders`).
  Đơn tạo ra là đơn thật, duyệt tay ở Worker `nostalgia-payment-admin`.
- Thứ tự ưu tiên địa chỉ dịch vụ (`src/nostalgia/social/configuration.py`,
  `read_configuration`): biến môi trường `NOSTALGIA_ACCOUNT_URL` / `NOSTALGIA_ROOM_SYNC_URL`
  > `services.json` của người dùng > `service-defaults.json` cài sẵn.

## Chơi chung

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
