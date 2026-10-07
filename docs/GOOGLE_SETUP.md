# Thiết lập đăng nhập Google — chủ dự án làm một lần

Người chơi chỉ bấm **Tiếp tục với Google**, chọn tài khoản trong trình duyệt rồi
quay lại launcher. Không nhập URL, Client ID, secret hoặc mã đăng nhập trong launcher.
Google giữ bạn bè và danh tính Nostalgia; Microsoft/Ely.by vẫn dùng riêng để chơi Minecraft.

## 1. Chọn địa chỉ backend

Cần một Cloudflare Account Worker riêng, HTTPS, ví dụ
`https://nostalgia-account-preview.<subdomain-của-bạn>.workers.dev` hoặc domain riêng.
Đây là ví dụ cấu trúc địa chỉ, chưa phải dịch vụ đang chạy. Dùng tài nguyên staging riêng.
Kho private `JunXmas/nostalgia-backend` có `GOOGLE_ONLY_SETUP.md` và mã Worker.
Không dùng URL GitHub hoặc relay làm callback Google.

## 2. Tạo OAuth client

1. Vào [Google Cloud Console](https://console.cloud.google.com/), tạo/chọn project Nostalgia.
2. **Google Auth Platform → Branding**: tên ứng dụng, email hỗ trợ, email nhà phát triển.
3. **Audience → External**. Ở chế độ Testing, thêm email người thử trong **Test users**.
4. **Data Access**: chỉ dùng `openid`, `email`, `profile`; không cần Gmail/Drive.
5. **Clients → Create client → Web application** (không chọn Desktop).
6. **Authorized redirect URIs**: origin account Worker + `/v1/auth/google/callback`.
   Ví dụ cấu trúc: `https://accounts.<domain-của-bạn>/v1/auth/google/callback`.
   Phải khớp chính xác HTTPS, hostname và đường dẫn. Không thêm dấu `/` cuối callback.
7. Lưu **Client ID**; đặt **Client Secret** trong Worker secret `GOOGLE_CLIENT_SECRET`.
   Không commit file JSON tải từ Google, không gửi secret trong chat, không nhúng vào app.

Luồng này dùng trình duyệt ngoài, nên không cần JavaScript origins cho launcher.
Trước khi mở rộng cho người chơi, chuyển Audience sang Production và hoàn tất yêu cầu
branding/domain/privacy policy mà Google Console hiển thị. Testing chỉ cho tester được thêm.

## 3. Cấu hình backend

- `PUBLIC_URL`: origin account Worker, không có đường dẫn hoặc dấu `/` cuối.
- `GOOGLE_CLIENT_ID`: Client ID Web application.
- `GOOGLE_CLIENT_SECRET`: Worker secret, chỉ ở server.
- D1 và các binding theo hướng dẫn kho private; `PLUS_ENABLED = "false"` trên
  cả account Worker và authorizer. Không cần khóa payOS cho Google-only.
- Triển khai vào staging sau khi cấu hình; không thay relay production.

## 4. Đóng gói địa chỉ sẵn cho người chơi

GitHub repo **Settings → Secrets and variables → Actions → Variables**:

| Variable | Giá trị |
|---|---|
| `NOSTALGIA_ACCOUNT_URL` | Origin HTTPS account Worker đã chạy |
| `NOSTALGIA_ROOM_SYNC_URL` | Origin HTTPS relay staging nếu thử lời mời/chơi chung |

Workflow build đưa **hai URL công khai** vào `service-defaults.json` trong bộ cài.
Client ID/Secret không đặt trong GitHub variable này. Khi chưa có account URL, build
ghi rõ Google chưa khả dụng; không gửi người dùng tới một hostname giả.

Thay variable sau khi tạo draft **không cập nhật bộ cài đã tạo**. Cần build draft mới
với tag mới sau khi backend và variable đã sẵn sàng. Mã nguồn local có thể thử bằng
`NOSTALGIA_ACCOUNT_URL`/`NOSTALGIA_ROOM_SYNC_URL`; người chơi không cần làm việc đó.

## 5. Thử đăng nhập thật

1. Gmail tester: bấm Google, kiểm domain Google, chọn tài khoản, chấp thuận.
2. Launcher tự nhận phiên, hiện tên Google và mã kết bạn; không yêu cầu copy mã.
3. Hủy ở Google: launcher báo hủy, cho thử lại. Không mở được trình duyệt: bấm Mở lại Google.
4. Máy thứ hai đăng nhập cùng Google: phiên dịch vụ máy đầu phải bị thu hồi.
   Đây không phải đăng xuất Gmail hay tài khoản Minecraft.
5. Kiểm bạn bè/chat bằng hai tài khoản. Phiên lưu trong keyring hệ điều hành khi khả dụng.
6. Plus/checkout/sửa mod tự động/đồng bộ modpack Plus vẫn tạm khóa. Quét mod miễn phí còn dùng.

`redirect_uri_mismatch`: so chính xác callback trong Google và PUBLIC_URL.
`access_denied` khi Testing: thêm email vào Test users.
503 tại start: kiểm Worker secret, Client ID, PUBLIC_URL, D1 và deployment.

Mã preview rc8 hiện chỉ kiểm luồng bằng Google giả ở biên mạng, RSA/D1/Qt thật.
Chưa có OAuth client/backend production được cung cấp nên chưa thử Google thật.

Theo yêu cầu chủ dự án: chưa build bộ cài hoặc tạo release draft rc8.
