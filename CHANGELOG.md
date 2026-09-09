# Changelog

Mốc phát hành của Nostalgia Launcher. Phiên bản theo semver; tag `vX.Y.Z` kích hoạt
`.github/workflows/release.yml` (xem `docs/RELEASE.md`).

## 1.0.0 — 2026-09-09

Bản đầu tiên của lần viết lại từ đầu (rework) sau dự án `NostalgiaLauncher` cũ (08/2026).

### Chơi
- Tài khoản Microsoft, Ely.by (authlib-injector, kiểm sha256) và ngoại tuyến; nhiều tài khoản.
- Bản chơi Vanilla, Fabric, Quilt, Forge, NeoForge và bộ "Optimized" (Fabulously Optimized);
  mỗi bản chơi có thể đặt ở thư mục riêng (ổ khác) để đỡ đầy đĩa.
- Thư viện mod / resource pack / shader / modpack từ Modrinth và CurseForge (CurseForge đi qua
  máy chủ của dự án, không cần khoá API); nhập modpack `.mrpack` / `.zip`, kéo-thả vào cửa sổ.
- Chơi chung: LAN qua relay với mã phòng 18 ký tự, 10 luật bảo mật có test gác
  (`docs/MULTIPLAYER_SECURITY.md`).
- Thư viện skin trong launcher: cất, dùng ngay, upload lên Mojang; xem trước cape.

### Giao diện
- Trang chủ với ảnh hero và thẻ neo vào công trình; nút kiểu khối Minecraft.
- Hộp Tạo bản chơi: thẻ key art chính thức từng dòng phiên bản (minecraft.wiki), thẻ chọn sáng
  lên và nhấc khỏi ô, phiên bản con trượt xuống.
- Nhật ký game có lọc mức, thống kê chơi (giờ chơi, số lần, thế giới, mod), thông báo toast +
  chuông, tiếng giao diện mềm kiểu dashboard (công tắc riêng), Discord Rich Presence (tắt mặc
  định), tự cập nhật với SHA256SUMS bắt buộc.

### Kỹ thuật
- Lõi không phụ thuộc thư viện ngoài (HTTP bằng `http.client`); giao diện là tuỳ chọn
  (`PySide6-Essentials`).
- Kiến trúc 7 tầng có test gác ranh giới; mỗi file ≤ 200 dòng mã; bảng thuật ngữ tên gọi
  (`GLOSSARY.md`) có test gác; ruff + mypy strict; CI Python 3.12 / 3.13.
- Bộ cài từ workflow release, có chạy thử gói ngay trên từng hệ: Linux AppImage / .deb / .rpm /
  tar.gz / zip, macOS .dmg cho Apple Silicon và Intel, Windows setup.exe (Inno Setup) và zip;
  SHA256SUMS cho mọi file. Gói macOS (.app) không tự tráo, chỉ báo bản mới.

### Chưa có so với bản cũ (sẽ quay lại)
- Trình vẽ skin từng pixel, đa ngôn ngữ (giao diện hiện là tiếng Việt), gói macOS.
