# Changelog

Mốc phát hành của Nostalgia Launcher. Phiên bản theo semver; tag `vX.Y.Z` kích hoạt
`.github/workflows/release.yml` (xem `docs/RELEASE.md`).

## 1.0.4 — 2026-09-12

- Sửa lỗi `freetype.dll` khi chơi một số phiên bản: hai thư viện natives (LWJGL-freetype) cùng
  chứa `freetype.dll` nhưng kích thước khác nhau khiến launcher báo lỗi và không chạy được game.
  Giờ giữ bản lớn hơn (đầy đủ hơn) và ghi cảnh báo thay vì crash.
- Sửa lỗi build Windows (v1.0.3): PyInstaller + PySide6 đóng gói hai bản `freetype.dll` khác
  nhau khiến gói Windows không chạy.

## 1.0.2 — 2026-09-10

- Hộp hỏi lại (cài thêm mod đã có) giờ nằm ở cấp cửa sổ: phủ cả thanh bên, bấm ra ngoài không
  đóng và không lọt xuống phía sau; chỉ Thôi / Esc đóng, Enter đồng ý.
- Trang chủ: ô CHƠI TIẾP có thêm nhóm **SERVER** — các server đã thêm trong game (đọc
  `servers.dat`, icon thật của server), bấm là vào thẳng server (quick play multiplayer, 1.20+).
  Không ping, trang chủ vẫn không chạm mạng.
- Trang chủ: khi game đang chạy, nút CHƠI thành nút **DỪNG** (đỏ) — bấm là dừng tiến trình
  game (SIGTERM cả cây, hết ân huệ thì SIGKILL); dừng chủ động không bị coi là sự cố.
- Thư viện: mod đã có trong bản chơi thì nút "Đã cài" xám vẫn bấm được; app hỏi lại "đã tồn
  tại" trước khi cài đè.

## 1.0.1 — 2026-09-10

- Trang chủ: ảnh hero giữ nguyên 2528 px, làm nét thích nghi, vẽ có mipmap — sắc nét gấp đôi
  ở cỡ hiển thị.
- Test import modpack hết rớt ngẫu nhiên trên CI (chờ hết bận rồi mới chờ tín hiệu).

## 1.0.0 — 2026-09-09

Bản 1.0.0 được phát hành lại ba lần trong ngày (logo khối lá, rồi ô CHƠI TIẾP) trước khi
đánh số riêng; nội dung cuối cùng của 1.0.0 gồm cả:

- Trang chủ: ô **CHƠI TIẾP** thay ô "Phiên bản đã tải" — các thế giới chơi gần nhất trên mọi bản
  chơi (đọc `level.dat` bằng bộ đọc NBT tối giản, có trần kích thước / độ sâu), mỗi thế giới một
  nút khối Minecraft nhấc lên khi rê chuột, lún khi ấn; bấm là vào thẳng thế giới (quick play,
  Minecraft 1.20+; đời cũ mở game bình thường). Bỏ nút tải trước phiên bản (CLI `nostalgia
  install` vẫn còn).
- Logo là khối lá Minecraft (thanh bên, icon cửa sổ, bộ cài, README).

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
