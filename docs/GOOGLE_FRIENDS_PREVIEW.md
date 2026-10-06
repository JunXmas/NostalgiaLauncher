> Tài liệu review giai đoạn trước. Bản rc2 đã bổ sung runtime release, payOS, hồ sơ Plus và sửa mod.
> Trạng thái hiện tại và hướng dẫn thử: [DRAFT_TEST_GUIDE.md](DRAFT_TEST_GUIDE.md).

# Google, bạn bè và Plus — bản preview để duyệt

2026-10-06. Thay đổi chỉ ở workspace, chưa build installer, push, tạo release hay deploy.
Người dùng đính chính: mở LAN không hiện mã, **không phải** game tự ngắt sau 15 phút.
Không dùng các bài soak cũ làm bằng chứng nguyên nhân của báo cáo mới.

## Trải nghiệm đã triển khai

- Tài khoản **Nostalgia qua Google** giữ bạn bè, chat và quyền Plus trên D1. Tài khoản
  Minecraft/Microsoft/Ely.by/ngoại tuyến vẫn dùng cho nhân vật và khởi chạy game;
  không gửi token Minecraft cho dịch vụ tài khoản hay thanh toán.
- Cả hai kiểu giao diện trong preview mở trang Bạn bè/Chơi chung. Bản release hiện hành
  vẫn giữ đường vào cũ, chưa tự bật một dịch vụ chưa được cấu hình.
- Thêm bạn bằng mã kết bạn riêng, cần người nhận chấp nhận. Đây là mã tài khoản để
  tìm bạn, không phải mã phòng chơi. Không tìm bằng email hoặc công khai Google sub.
- Bạn bè đã chấp nhận được chat miễn phí, xem trạng thái trực tuyến, mời/nhận lời mời.
  Có hủy/từ chối yêu cầu, bỏ kết bạn và chặn. Chat lưu tối đa 30 ngày, 100 tin gần nhất;
  không phải chat mã hóa đầu cuối. Preview chưa có màn quản lý bỏ chặn.
- Chat/danh sách kiểm tra mỗi 3 giây khi trang bạn bè mở, 15 giây ở trang khác;
  online mất sau 45 giây không heartbeat. Lời mời hiện cả khi đang ở Home.
- Bấm **Mở phòng** trong launcher rồi mở LAN trong Minecraft. Khi đã nhận LAN và nối
  relay, nút mời mới hoạt động. Người nhận bấm **Vào phòng**, không phải chép mã phòng.
- Nếu multicast bị chặn/bind lỗi, vẫn giữ màn chờ, cho nhập cổng game báo. Chỉ probe
  `127.0.0.1`, xác minh Minecraft Status trước khi mở relay; không quét cổng hoặc nhận
  host/IP từ bạn bè. Cách dự phòng này dành cho Minecraft 1.7+.
- Chủ phòng Plus chia sẻ ảnh chụp pack; khách Google Free nhận lời mời vẫn thấy ô
  đồng bộ miễn phí. Vẫn tạo bản chơi riêng và kiểm hash như preview trước. Cả nhóm
  cần cùng game/loader/mod; đồng bộ không chứng minh mọi mod chạy tương thích.

## Một phiên hoạt động, quyền ở máy chủ

Google OAuth dùng trình duyệt ngoài launcher, authorization code + PKCE, state, nonce.
Backend đổi code và kiểm chữ ký RS256 từ Google JWKS, issuer, audience, thời hạn, nonce,
Google sub và email_verified. Không chấp nhận tên/email/sub/paid do client tự khai.
Không giữ access/refresh token Google; phiên Nostalgia là bearer ngẫu nhiên riêng.

Desktop giữ verifier ngẫu nhiên; API start chỉ nhận SHA-256 challenge. Callback không trả
bearer trong URL. Poll có proof mới claim một lần. D1 batch cấp phiên mới và thu hồi mọi
phiên cũ của cùng account nguyên tử. Plus và bạn bè giữ nguyên vì account dựa vào Google sub,
không phụ thuộc email, nickname hay nhân vật Minecraft.

- Phiên cũ bị API từ chối ngay sau batch. UI phát hiện ở lần poll kế tiếp, thường trong
  3–15 giây khi không có request đang chờ; lỗi mạng không bị hiểu là quyền Plus hợp lệ.
- UI thu hồi trạng thái, dừng phòng và hủy đồng bộ khi nhận 401. Game/bản chơi local
  không bị xóa. Quyền Plus gắn account, không nhân đôi khi chuyển máy.
- Token phiên dùng kho Windows Credential Manager, macOS Keychain hoặc kho SecretService/
  KWallet hỗ trợ qua keyring. Từ chối backend plaintext. Không có kho an toàn thì chỉ giữ
  token trong RAM và cần đăng nhập lại khi mở launcher. Scope gồm backend URL và config dir.
- Phiên hết hạn sau 30 ngày. Chưa có gia hạn im lặng; đăng nhập Google lại sẽ cấp phiên mới.
- Relay kiểm phiên host từng upload/commit và hash phiên đã publish từng download của
  khách. Đăng nhập host trên máy mới chặn tải pack qua phiên cũ dù Plus của account còn hạn.

Đây là giới hạn **phiên Nostalgia**, không phải quyền đăng xuất Gmail/Google trên máy khác.
Không thể hứa chống mọi can thiệp: chủ máy có thể lấy/copy bearer hoặc chạy bản sửa app;
server kiểm phiên và entitlement vẫn là nơi quyết định quyền dịch vụ. Không có HWID/attestation.
Bản modpack đã tải có thể sao chép thủ công, không bị DRM khóa lại.

## Lời mời không lộ mã phòng

Host vẫn sinh phòng và secret HMAC của giao thức relay, nhưng mã được mã hóa tới public
key X25519 hiện hành của máy bạn nhận. X25519 + HKDF-SHA256 + AES-GCM; AAD ràng buộc
room ID, người nhận và khóa nhận. API không nhận `room_code` plaintext. Backend lưu
ciphertext và vé kiểm host trong envelope mã hóa AES-GCM bằng secret Worker riêng.

API kiểm bạn bè, block, phiên host hiện hành, khóa máy nhận, vé socket host thật tại
relay. Chỉ đúng người nhận lấy envelope, một lần, trong 5 phút. Đóng phòng, đổi host,
đăng nhập máy mới hoặc thay khóa nhận làm lời mời không còn dùng được. Máy nhận mới
khởi động lại cần bạn gửi lại lời mời; không đồng bộ khóa riêng ephemeral lên server.

Dịch vụ danh tính vẫn được tin khi liên kết tài khoản với public key. Không tuyên bố
chống một dịch vụ danh tính chủ động thay khóa hoặc thiết bị người chơi đã bị chiếm.

## Bốn gói và quyền lợi riêng — cập nhật theo yêu cầu mới

| Gói | Giá | Quyền lợi thêm được đề xuất trong preview |
|---|---:|---|
| Khởi đầu · 1 tháng | 29.000đ | Toàn bộ Plus cốt lõi |
| Đồng hành · 6 tháng | 69.000đ | Huy hiệu Đồng hành và màu hồ sơ |
| Tiên phong · 12 tháng | 109.000đ | Huy hiệu Tiên phong, màu hồ sơ, tham gia preview sớm |
| Sáng lập · mua đứt | 209.000đ | Huy hiệu Sáng lập, màu hồ sơ, preview sớm, cập nhật Plus về sau |

Các gói giữ cùng khả năng sửa mod được hỗ trợ và chủ phòng đồng bộ modpack; quyền lợi
thêm hướng đến hồ sơ và đồng hành phát triển, không khóa chat/chơi chung miễn phí.
Không tự gia hạn. Mua đứt không hết hạn trong thời gian dịch vụ hoạt động; không bao gồm
máy chủ Minecraft riêng, AI/hỗ trợ không giới hạn hay miễn giới hạn chống lạm dụng.
Không tước tính năng Plus đã mua chỉ để đưa sang một cấp cao mới.

**Đã có mã**: bốn offer từ catalog server, chọn giá/gói, biên nhận mua đứt, đọc membership
và huy hiệu của chính tài khoản theo quyền server, authorizer và relay chấp nhận lifetime.
**Chưa có**: màn tùy chỉnh màu hồ sơ, hiển thị huy hiệu bạn bè, kênh cấp preview sớm,
cổng thanh toán và engine sửa mod. Các quyền lợi thêm trong cửa sổ ghi rõ đề xuất preview,
chưa quảng cáo như tính năng đang bán. Chưa nhận tiền thật.

Mua đứt dùng `duration_months=0` **và** `lifetime=true` rõ ràng; số 0 thiếu cờ không được
chấp nhận. Biên nhận paid phải có cùng cờ và `active_until=0` đúng kiểu integer, không
nhận null/boolean/chuỗi. Cờ giao diện không cấp quyền: D1 phải có entitlement không bị
thu hồi và membership mua đứt hợp lệ. Thu hồi hoặc hoàn tiền phải cập nhật cả hai trong
transaction backend. Phiên một máy vẫn áp dụng với lifetime; đăng nhập máy mới ngắt
quyền đồng bộ ở phiên cũ như các gói thời hạn.

Backend thanh toán cần dùng **account_id Google đã xác thực**, cùng D1. Webhook được
xác minh mới ghi entitlement và metadata gói nguyên tử. Client chỉ gửi offer ID; không
thể tạo đơn trước khi nhận offer thật. Nút **Kiểm tra thanh toán** chỉ tra trạng thái.
Gói thời hạn cần tháng lịch UTC, chặn ngày cuối tháng hợp lệ; đơn/giao dịch idempotent.
Đây vẫn là yêu cầu của backend thanh toán chưa triển khai, không phải engine đã chạy.

## Bố cục bạn bè đã thu gọn

- Tài khoản Google chuyển vào vùng mở rộng; không chiếm cả thẻ ở đầu trang thường xuyên.
- Thêm bạn dưới nút +, yêu cầu kết bạn gấp lại theo số lượng; danh sách dài có scroll riêng.
- Desktop có danh sách và chat; cửa sổ hẹp chỉ hiện danh sách hoặc cuộc trò chuyện đang chọn.
- Chat có ô nhập/nút Gửi cùng hàng, tùy chọn chặn/làm mới dưới nút ···. Đổi người nhận
  xóa bản nháp tránh gửi nhầm. Ở cửa sổ hẹp, thu gọn lời mời và giữ ô nhập trong vùng nhìn.
- Phòng hiện trạng thái ngắn; chỉ mở tùy chọn khóa phòng, modpack hoặc nhập cổng LAN khi cần.
- Palette cũ, mica và model Minecraft được giữ. Không thêm một dashboard thẻ mới.

## Cấu hình để thử thật còn thiếu

Kho private `/workspace/NostalgiaBackend/account-service`: OAuth/account/friends/chat;
`plus-authorizer`: đọc phiên/quyền; `multiplayer-relay`: vé host và modpack R2.

Cần Google OAuth **Web application** client, domain HTTPS callback
`/v1/auth/google/callback`, client secret trong Worker secret, shared D1, private R2,
service bindings và INVITE_KEY. Không gửi secret qua chat, không nhúng vào launcher.
Google consent app cần cấu hình người thử nghiệm/duyệt theo phạm vi triển khai.
Chưa cấu hình/deploy tài nguyên hoặc chạy đăng nhập Google thật.

Runner: `python bench/ui_minimal_preview.py --accounts-url https://<account-service>
--room-sync-url https://<relay>`. Phiên Google tự nối payment/sync gateway. Preview UI
mẫu dùng `--social-demo --payment-demo`; token và QR demo không mở được dịch vụ thật.

## Kiểm tra và ảnh

- Kết quả kiểm tra cuối được ghi tại [review gói mua đứt/bố cục](PLUS_LIFETIME_REVIEW.md).
- 16 kiểm tra Node/workerd/D1/R2, gồm OAuth với nhà cung cấp giả nhưng ký/kiểm RSA thật,
  claims sai/chữ ký sửa, poll replay/song song, phiên cũ, giữ Plus/bạn bè khi đổi phiên,
  chat ngoài quan hệ bạn bè, vé giả, sai người nhận và thu hồi phiên host đã publish.
- X25519/AES-GCM chạy thật; máy khác hoặc AAD sai không giải được. Gateway đi HTTPS cục bộ,
  kiểm request không có room_code plaintext và giải mã được ở đúng máy nhận.
- Qt chạy cả software và OpenGL. Ảnh dưới là Qt thật với **dữ liệu mẫu PREVIEW**;
  không chứng minh OAuth/thu tiền/Minecraft nhiều máy trên production đã hoạt động.
- Mypy và Ruff qua; không cảnh báo QML trong 6 capture cuối. Kho OS Windows/macOS
  kiểm qua adapter giả; chưa chạy launcher trên Windows/macOS thật ở lượt này.

[Bạn bè thu gọn](preview/minimal/friends-compact-preview.png) ·
[Chờ LAN](preview/minimal/friends-compact-lan.png) ·
[Chat cửa sổ nhỏ 150%](preview/minimal/friends-compact-small-chat.png) ·
[Danh sách nhỏ 150%](preview/minimal/friends-compact-small-list.png) ·
[Bốn gói Plus](preview/minimal/plus-four-plans.png) ·
[Biên nhận mua đứt](preview/minimal/plus-lifetime-receipt.png)
