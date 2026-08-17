# Nostalgia backend (Cloudflare Worker)

Một Worker duy nhất phục vụ **skin** (để người chơi offline nhìn thấy skin của nhau
qua CustomSkinLoader) và **khôi phục danh tính** (gắn với Google `sub`). Miễn phí ở
mức dùng của một cộng đồng nhỏ (Workers free + R2 free 10GB + KV free).

## Deploy (một lần)

```bash
npm i -g wrangler
wrangler login
wrangler r2 bucket create nostalgia-skins
wrangler kv namespace create META      # dán "id" trả về vào wrangler.toml
cd backend && wrangler deploy
```

Sau khi deploy bạn được một URL, ví dụ `https://nostalgia-backend.<you>.workers.dev`
(nên gắn domain riêng). Đó là **BACKEND_URL**.

## API

Skin (chuẩn CustomSkinLoader *CustomSkinAPI*, root = BACKEND_URL):
- `GET  /{username}.json` → `{username, skins:{default|slim:"<hash>"}}`
- `GET  /textures/{hash}` → PNG
- `PUT  /skin/{username}?variant=classic|slim` → tải skin lên (body = PNG)

Danh tính:
- `GET  /identity/{sub}` → `{player_id, display_name, accounts}`
- `PUT  /identity/{sub}` → body `{player_id, display_name, accounts}`

## Bảo mật (không nhúng secret nào ở client)

Ghi skin phải kèm `Authorization: Bearer <minecraft_access_token>` — Worker gọi
`api.minecraftservices.com/minecraft/profile` để xác minh token đó đúng là chủ của
`username`. Vậy không cần một "upload key" chung nhét trong app (thứ sẽ bị moi ra từ
binary). Tài khoản **offline** không có token thật → chỉ ghi được tên **chưa** thuộc
về tài khoản premium nào (trust-on-first-use).

## Nối vào launcher (làm khi đã có BACKEND_URL)

1. Cấu hình `BACKEND_URL` trong Settings (hoặc biến môi trường).
2. Sau khi đổi skin, launcher `PUT /skin/{username}` kèm token → skin lên R2.
3. Ship **CustomSkinLoader** cho mỗi instance, cấu hình một nguồn *CustomSkinAPI*
   trỏ tới BACKEND_URL. CSL sẽ tự lấy skin theo tên khi render người chơi khác →
   offline nhìn thấy skin của nhau trên mọi server.
4. (Tuỳ chọn) khi Google-link, `PUT /identity/{sub}`; máy mới đăng nhập Google →
   `GET /identity/{sub}` để khôi phục `player_id` + danh sách account.

## Google OAuth — dùng client loại "Desktop app"

Ở Google Cloud Console tạo OAuth client **type = Desktop app**. Với loại này
`client_secret` **không** được coi là bí mật (Google cho phép ship trong app cài),
và PKCE mới là lớp bảo vệ — `nostalgia/google_auth.py` đã dùng PKCE sẵn. Đừng dùng
client loại "Web application" (secret của nó là bí mật thật, không được phát tán).
