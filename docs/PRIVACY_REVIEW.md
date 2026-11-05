# Báo cáo review thống kê tự nguyện và giao diện launcher

Ngày kiểm: 05/11/2026. Bản sửa chưa phát hành hoặc deploy production.

## Phát hiện ban đầu

- Launcher hiện tại không có endpoint analytics độc lập. Snapshot bạn bè `GET /v1/me`
  được tải sau đăng nhập, thao tác và refresh; backend gọi `recordActivity()` từ
  `friend.snapshot()` và ghi ngày UTC+7, account_id, first_seen, không có consent riêng.
- Dashboard cũ đọc số tài khoản/online/tuần/tháng cùng lượt tải GitHub; dữ liệu này không
  chứng minh số bản cài hoặc số người dùng launcher.
- WebSocket ping và kết nối phòng phục vụ tính năng. Timer ServerBridge mang tên heartbeat
  chỉ cập nhật UI/log cục bộ. Presence Worker cũ giữ tên/trạng thái/phòng trong bộ nhớ;
  không thấy launcher hiện tại gọi nó.
- Discord IPC là tính năng riêng, hiện bật mặc định. Đăng nhập, cập nhật GitHub, tải nội
  dung, phòng chơi và sửa mod theo yêu cầu đều là kết nối chức năng, không phải consent.
- Sửa mod gửi metadata/hash/tên file mod và chẩn đoán phụ thuộc đã rút gọn sau thao tác yêu
  cầu. Không thấy tự upload crash report hoặc toàn bộ log của launcher.

## Thay đổi thực tế

- Ba trạng thái local `unselected/declined/accepted`, mới/nâng cấp không suy diễn consent.
- Cài đặt và dialog một lần VI/EN: hai nút ngang mức nổi bật; X/Escape lưu từ chối.
  Hoãn đăng nhập, tác vụ quan trọng, lỗi và modal khác. Đã chọn ở Cài đặt không hỏi lại.
- Mẫu schema tạo cục bộ, không chứa mã thật hoặc tạo sự kiện chờ. Không có sự kiện chạy game.
- Chỉ `installation_active`: ngày UTC, phiên bản launcher, nhóm OS, schema và mã ngẫu
  nhiên 128 bit theo ngày; không có mã gốc hoặc thông tin tài khoản/phần cứng.
- Hoạt động nghĩa launcher đang chạy sau consent, kể cả để mở ở nền qua ngày UTC mới;
  không phải thao tác của người chơi, thời lượng chơi hoặc đã vào Minecraft.
- Kiểm consent ngay trước transport; khi tắt hủy timer/token/thế hệ, xóa mã và dấu đã thử.
  Không hàng đợi, retry nền hoặc gửi bù; request đã rời máy có thể không thu hồi.
- Backend bỏ ghi ngầm từ snapshot; endpoint mới validate allowlist/512 byte, D1 transaction
  chống lặp nguyên tử, băm ngày+mã TTL 24 giờ, cron mỗi giờ, tổng hợp 90 ngày.
- Dashboard tách dữ liệu v1 UTC, lịch sử tài khoản UTC+7 và lượt tải; ngày hiện tại có nhãn
  chưa hoàn tất. Không có người riêng biệt tuần/tháng, retention hoặc tổng khách+tài khoản.
- English mặc định cho cài mới, giữ tiếng Việt đã lưu; nút Nos ở danh sách rút gọn cạnh
  metadata, có kiểm tra không chồng chữ/actions ở scale 100/125/150%, VI/EN.

## Endpoint và payload minh họa

Luồng mới dùng `POST https://<origin-da-xac-minh>/v1/usage`. Đây là contract, không phải
origin đã cấu hình. Client hiện endpoint rỗng/ready=false; backend USAGE_ENABLED=false.
Không hiện lời mời cho dịch vụ chưa sẵn sàng. Backend production cũ có thể vẫn ghi thống kê
snapshot đến khi operator deploy bản đã sửa; lựa chọn client không điều khiển mã server cũ.

```json
{"schema_version":1,"event":"installation_active","day":"2026-11-05","launcher_version":"1.2.2","os_group":"windows","daily_id":"0123456789abcdef0123456789abcdef"}
```

Đây là bản cài tự nguyện/ngày, không phải toàn bộ người chơi hoặc người riêng biệt. Xóa cấu
hình/cài lại/tắt rồi bật có thể tạo mã mới. Lỗi mạng và giới hạn lạm dụng có thể làm thiếu số liệu.

## Kiểm chứng

- Toàn bộ pytest không Internet: **2.195 passed, 2 skipped, 1 deselected**, 967,60 giây.
- Ruff check/format đạt; mypy đạt **768 file**; kiểm danh mục/ảnh cosmetic đạt.
- HTTPS localhost thật: unselected/declined tạo **0 request analytics**, tải nội dung vẫn
  hoạt động; accepted nhận đúng allowlist, không Authorization/Cookie; tắt không gửi thêm.
- Mock transport xác nhận hủy job cũ kể cả bật lại, kiểm consent cuối cùng, đổi mã theo UTC,
  dedup trong ngày qua mở lại và lỗi analytics không tạo popup/retry/chặn chơi.
- Qt thật: consent VI/EN, X/Escape/keyboard, payload local, timing/modal/login/busy, settings
  và cửa sổ nhỏ/chữ lớn. Đã xem PNG; 24 bố cục Nos đạt, không cảnh báo QML.
- Backend Miniflare/D1 tạm: **28 passed**, gồm retry đồng thời, schema, cap nguyên tử, TTL,
  snapshot không ghi analytics và dashboard tách phương pháp.
- Dashboard HTML/CSS/module thật với API mẫu: render 1440/1024px, đã xem PNG.
- Wheel/sdist build đạt, tài nguyên usage JSON/QML có trong wheel. PyInstaller release
  build đạt; binary mở offscreen với cấu hình QA riêng, báo smoke ok.
- Các lỗi kỳ vọng tiếng Việt cũ trong lượt full đầu được sửa cho mặc định English; lượt
  full sau đạt như trên. Không giảm hoặc bỏ assertion để bỏ qua lỗi chức năng.

## Giới hạn xác minh

Không deploy, không sửa dữ liệu production, không xác nhận schema/migration mới đang chạy.
Log ứng dụng endpoint mới không ghi payload/định danh; điều này không chứng minh Cloudflare,
reverse proxy, D1 trace/backup hoặc hệ thống xuất log không giữ dữ liệu/IP. Thời hạn bảng
hoạt động phụ thuộc cron thành công, không phải bảo đảm xóa mọi bản sao hạ tầng.

Xem [PRIVACY.md](PRIVACY.md), [schema](usage-schema.json) và hướng dẫn rollout trong backend.

Kiểm cấu hình Cloudflare read-only ngày 05/11: ba Worker không trả cấu hình observability
explicit, logpush=false, không tail consumer. API Logpush toàn account trả 403; chưa kiểm
live Tail, nội dung log, reverse proxy, D1 trace hoặc backup. Không diễn giải thành “không lưu IP”.

## File đã sửa — launcher

- `CHANGELOG.md`
- `README.md`
- `docs/PRIVACY.md`
- `docs/PRIVACY_REVIEW.md`
- `docs/site/index.html`
- `docs/usage-schema.json`
- `packaging/nostalgia-ui.spec`
- `src/nostalgia/api.py`
- `src/nostalgia/facade/usage.py`
- `src/nostalgia/model/usage.py`
- `src/nostalgia/settings/store.py`
- `src/nostalgia/ui/app.py`
- `src/nostalgia/ui/appearance_bridge.py`
- `src/nostalgia/ui/qml/TranslationProvider.qml`
- `src/nostalgia/ui/qml/app/InstanceTile.qml`
- `src/nostalgia/ui/qml/app/Main.qml`
- `src/nostalgia/ui/qml/app/UsageConsent.qml`
- `src/nostalgia/ui/qml/app/UsageData.qml`
- `src/nostalgia/ui/qml/app/UsageSettings.qml`
- `src/nostalgia/ui/qml/i18n/en.json`
- `src/nostalgia/ui/qml/i18n/vi.json`
- `src/nostalgia/ui/qml/pages/SettingsPage.qml`
- `src/nostalgia/ui/settings_bridge.py`
- `src/nostalgia/ui/translations.py`
- `src/nostalgia/ui/usage_bridge.py`
- `src/nostalgia/ui/usage_settings_bridge.py`
- `src/nostalgia/usage/__init__.py`
- `src/nostalgia/usage/collector.py`
- `src/nostalgia/usage/configuration.py`
- `src/nostalgia/usage/defaults.json`
- `src/nostalgia/usage/state.py`
- `tests/settings/test_settings_store.py`
- `tests/source_tree.py`
- `tests/ui/test_accounts_page.py`
- `tests/ui/test_default_language.py`
- `tests/ui/test_friend_invite.py`
- `tests/ui/test_guest_sync_popup.py`
- `tests/ui/test_main_window.py`
- `tests/ui/test_nos_toggle_flow.py`
- `tests/ui/test_notifier.py`
- `tests/ui/test_payment_layout.py`
- `tests/ui/test_payment_manual_ui.py`
- `tests/ui/test_qml.py`
- `tests/ui/test_social_ui.py`
- `tests/ui/test_stop_game.py`
- `tests/ui/test_tray.py`
- `tests/ui/test_usage_consent.py`
- `tests/usage/test_choice.py`
- `tests/usage/test_collector.py`
- `tests/usage/test_https_transport.py`

## File đã sửa — backend

- `.gitignore`
- `README.md`
- `account-service/src/admin/analytics.js`
- `account-service/src/admin/web/2b7e38a43b1aba889503f902c8d0293d2a3a1f4e-style.css`
- `account-service/src/admin/web/2c3bae78b875d638cde21ff4bd365cb1c739d98f-analytics.txt`
- `account-service/src/admin/web/3f7613dc26df238244bb3a8326739b851f480584-index.html`
- `account-service/src/admin/web/4832bb1959133e32fe361e9fda9dd98badcb87fc-app.txt`
- `account-service/src/analytics.js`
- `account-service/src/friend.js`
- `account-service/src/index.js`
- `account-service/src/usage.js`
- `account-service/wrangler.toml`
- `docs/PRIVACY.md`
- `docs/USAGE_ROLLOUT.md`
- `docs/usage-schema.json`
- `migrations/0002_optional_usage.sql`
- `tests/optional-usage.test.js`
- `tests/recovery.test.js`
- `tests/runtime.js`
- `tests/schema.sql`
