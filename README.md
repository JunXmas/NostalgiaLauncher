# Nostalgia Launcher

Launcher Minecraft Java Edition viết bằng Python. Nhận **cả tài khoản đã mua và
chưa mua game**:

| Loại tài khoản | Chế độ chạy |
|---|---|
| Microsoft, đã mua game | Full game, chơi được server online |
| Microsoft, chưa mua game | **Demo mode chính thức** (thế giới cố định, ~100 phút) |
| Đã mua nhưng đang mất mạng | Full game từ phiên đã cache (singleplayer/LAN) |
| **Hồ sơ offline** | Full game offline — chỉ mở khi launcher đã có tài khoản sở hữu game |

Demo mode là đường Mojang cung cấp sẵn cho người chưa mua: tài khoản Microsoft
bất kỳ đều đăng nhập được, chỉ là chưa có profile Minecraft. Launcher phát hiện
điều đó qua `/minecraft/profile` trả về 404, rồi bật cờ `--demo`.

## Cổng chứng minh quyền sở hữu

Hồ sơ offline theo đúng ngữ nghĩa của [PrismLauncher](https://github.com/PrismLauncher/PrismLauncher),
khoá ở hai tầng:

1. **Lúc thêm** — `AccountStore.add_offline()` ném `OwnershipRequired` nếu chưa có
   tài khoản Microsoft nào sở hữu game. Tài khoản demo không tính là chủ sở hữu.
   Đối chiếu: `AccountListPage::on_actionAddOffline_triggered()` +
   `AccountList::anyAccountIsValid()`.
2. **Lúc khởi động** — `AccountStore.resolve_identity()` kiểm tra lại. Nếu tài khoản
   chủ sở hữu đã bị xoá, mọi hồ sơ offline tự tụt xuống demo mode thay vì chạy full
   game. Đối chiếu: `LaunchController::decideLaunchMode()`.

UUID offline sinh giống hệt `MinecraftAccount::uuidFromUsername`: MD5 của
`OfflinePlayer:<tên>`, set version 3 và variant RFC 4122 — cùng giá trị mà server
vanilla tự sinh ở `online-mode=false`.

## Cài đặt

```bash
pip install -r requirements.txt
```

### Đăng ký Azure application (bắt buộc, miễn phí)

**Bước 1 — tạo app.** Vào https://portal.azure.com → **App registrations** →
*New registration*:

| Trường | Chọn |
|---|---|
| Name | tuỳ ý, ví dụ `nostalgia-launcher` |
| Supported account types | **Personal Microsoft accounts only** |
| Redirect URI | bỏ trống — device code flow không cần |

**Bước 2 — bật public client.** Vào **Authentication** → kéo xuống
*Advanced settings* → **Allow public client flows: Yes** → Save. Không bật thì
Microsoft từ chối ngay ở bước xin mã.

**Bước 3 — lấy ID.** Tab **Overview**, copy *Application (client) ID*:

```bash
export MC_CLIENT_ID=<application-id>
```

**Bước 4 — xin duyệt dùng Minecraft API.** Đây là bước dễ bỏ sót nhất. Azure app
tạo mới **không** mặc định gọi được Minecraft Services; chưa duyệt thì
`api.minecraftservices.com` trả **403** ngay ở bước `login_with_xbox` — sau khi
đã qua Microsoft và Xbox Live thành công, nên rất dễ tưởng là lỗi code.

Nộp đơn tại **https://aka.ms/mce-reviewappid**, chờ Microsoft phản hồi, và sau
khi được duyệt còn cần tới 24 giờ để có hiệu lực.

Launcher nhận biết đúng tình huống này và báo thẳng nguyên nhân kèm link, thay vì
ném ra lỗi HTTP trống.

Hai chi tiết kỹ thuật đã làm đúng sẵn trong `auth.py`, nêu ra phòng khi bạn sửa:
tenant phải là `consumers` (không phải `common`), và scope phải chứa
`XboxLive.signin`. Không cần client secret.

Java: 1.16 trở xuống cần Java 8, 1.17–1.20.4 cần Java 17, 1.20.5+ cần Java 21.
Launcher tự dò trong `JAVA_HOME` và `/usr/lib/jvm`.

## Giao diện

![Giao diện Aero Glass](docs/screenshot.png)

```bash
./run-gui.sh
```

Script này chỉ làm một việc thêm: trỏ `LD_LIBRARY_PATH` vào `.venv/lib/extra`.
Qt6 cần `libxcb-cursor.so.0` mà máy chưa có gói `libxcb-cursor0`; bản sao thư viện
đã để sẵn ở đó nên không cần sudo. Muốn cài đàng hoàng thì
`sudo apt install libxcb-cursor0` rồi gọi thẳng `python -m nostalgia gui`.

Bố cục theo launcher chính thức (sidebar tài khoản, tab ngang, hero, thanh chơi),
chất liệu theo Aero Glass của Windows Vista/7:

- **Kính mờ thật, không phụ thuộc compositor.** Thay vì xin KWin/picom làm mờ nền
  desktop — thứ Cinnamon trên Mint không hỗ trợ — các tấm kính lấy nền từ ảnh hero
  của chính cửa sổ đã blur. Giống hệt về mắt nhìn, chạy như nhau trên mọi máy.
- **Vệt bóng cắt giữa** ở 50% chiều cao là chữ ký của Aero, dùng cho thanh ngang và
  nút. Panel dọc dùng ánh sáng hắt ngang — áp vệt cắt lên panel cao 600px thì thành
  đường nối giữa màn hình chứ không ra mặt kính.
- **Viền vát** sáng trên / tối dưới cho tấm kính có bề dày, cửa sổ bo góc 8px không
  khung, kéo bằng thanh trên.
- **Nút CHƠI** dựng đúng kiểu nút Vista: nửa trên sáng, cắt phựt, nửa dưới hắt sáng
  ngược, gờ sáng sát mép trong, quầng sáng toả ra khi rê chuột.
- **Ảnh nền sinh bằng thuật toán** (`ui/hero.py`) — đảo voxel phối cảnh, có sương xa.
  Không dùng artwork của Mojang, nên không vướng điều khoản phát tán.
- **Tiến trình là công dân hạng nhất**: thanh xác định kèm số file thật
  (`1 842 / 3 021`), ẩn hẳn khi rảnh thay vì đứng ở 0%.

Chấm trạng thái đổi màu theo tài khoản: xanh = đủ quyền, vàng = demo hoặc hồ sơ
offline đã hạ cấp, xám = chưa đăng nhập.

### Những gì bấm được

| Chỗ bấm | Việc |
|---|---|
| Tên tài khoản (góc trên trái) | Menu: đổi tài khoản, thêm tài khoản Microsoft, thêm hồ sơ offline, xoá |
| Ô phiên bản (cạnh nút CHƠI) | Menu 80 phiên bản, đánh dấu bản đã tải, chọn để đổi |
| Tab **Bản cài đặt** | Danh sách bản đã tải kèm dung lượng và bản Java cần; chọn hoặc xoá từng bản |
| Nút **CÀI FABRIC** | Chọn phiên bản game để cài Fabric loader, đánh dấu bản đã cài |
| Tab **Skin** | Dựng hình nhân vật từ skin thật của tài khoản (tải từ máy chủ Mojang) |
| Tab **Ghi chú** | Ghi chú phiên bản thật từ `launchercontent.mojang.com`, đọc được nội dung đầy đủ |
| **Tin tức** (sidebar) | Tin chính thức của Mojang; bấm để mở bài gốc |
| **Cài đặt** (sidebar) | RAM (thanh trượt, trần = nửa RAM máy), thư mục game, đường dẫn Java, hiện snapshot, đóng launcher khi chạy game |
| **CHƠI** | Tải phần còn thiếu rồi khởi động, tiến trình hiện theo số file thật |

Đăng nhập làm ngay trong GUI: hộp thoại hiện mã device code, tự mở trang
Microsoft và tự chép mã vào clipboard, rồi chờ bạn xác nhận.

Tin tức và ghi chú được cache 6 giờ ở `~/.cache/nostalgia-launcher`, nên mở lại không
phải chờ mạng và mất mạng vẫn xem được bản đã tải.

## Fabric

```bash
python -m nostalgia fabric 1.21.4     # hoặc bấm CÀI FABRIC trong tab Bản cài đặt
```

Fabric meta trả về một *profile json* chỉ chứa phần chênh lệch so với bản vanilla,
nối bằng khoá `inheritsFrom`. Launcher phải tự trộn hai JSON, và có ba chỗ dễ sai:

- **Thứ tự thư viện.** Thư viện của loader phải đứng **trước** vanilla trên
  classpath, vì Fabric thay thế một số lớp của game.
- **Thư viện kiểu maven.** Mojang khai báo sẵn `downloads.artifact`; Fabric chỉ cho
  toạ độ `group:artifact:version` cùng một URL gốc, phải tự dựng đường dẫn
  (`fabric.maven_path`). SHA1 thì Fabric có cung cấp nên vẫn kiểm được.
- **Jar của game.** Bản Fabric không có jar riêng — nó dùng lại jar vanilla. Khoá
  `jar` trong JSON đã trộn trỏ về đó, nên `versions/fabric-loader-…/` chỉ chứa
  metadata, không nhân đôi 25 MB jar.

## Kiểm tra cài đặt (`doctor`)

Soi từng mắt xích của luồng khởi động mà **không cần tài khoản nào** — đây là cách
kiểm tra launcher trong lúc phát triển, chính xác hơn nhiều so với việc nhìn xem
cửa sổ game có mở lên không.

```bash
python -m nostalgia doctor 1.21.4
python -m nostalgia doctor fabric-loader-0.19.3-1.21.4 --hashes --command
```

Trong GUI: **Cài đặt** → nút **KIỂM TRA CÀI ĐẶT**.

Nó kiểm: metadata (kể cả kế thừa Fabric), Java đúng phiên bản, client jar, đủ
thư viện trên classpath, SHA1 từng thư viện, natives đã giải nén, asset index và
từng file asset, dựng lệnh không sót placeholder, và mainClass. Thoát với mã 1
nếu có lỗi nên cắm vào CI được. Access token luôn bị che khi in lệnh.

Ví dụ nó bắt được ngay:

```
  ✓ Metadata phiên bản: release, mainClass KnotClient, kế thừa từ 1.21.4
  ✗ Java: Không tìm thấy Java 21
  ✓ Client jar: 1.21.4.jar, 27.0 MB
  ✗ Thư viện: thiếu 70/78
  ✓ Hash thư viện: khớp hết
  ✗ Assets: thiếu asset index 19.json
  ✓ Dựng lệnh: 35 tham số, không sót placeholder
```

## Chạy nhiều instance cùng lúc

Bấm **CHƠI** nhiều lần là mở thêm instance; launcher đếm và hiện số đang chạy.
Dùng để test LAN, thử mod, hoặc chạy hai client nói chuyện với nhau.

Các instance dùng chung `game_dir` thì **tranh nhau khoá file world**, nên chỉ vào
được server/LAN, không mở world đơn. Muốn hai client hoàn toàn độc lập thì tách
thư mục qua CLI:

```bash
python -m nostalgia --game-dir ~/.mc-a play 1.21.4 --account jun
python -m nostalgia --game-dir ~/.mc-b play 1.21.4 --account Lan
```

### Mô hình xác thực, cho rõ ràng

Hồ sơ offline **không** vào được server `online-mode=true`, và điều này không sửa
được từ phía client vì client không tham gia vào quyết định:

```
Client → Server         Encryption Request
Client → sessionserver  /session/minecraft/join      (accessToken thật + serverId)
Server → sessionserver  /session/minecraft/hasJoined?username=…&serverId=…
Mojang không xác nhận → server ngắt: "Failed to verify username"
```

Hồ sơ offline mang `accessToken = "0"` nên bước `join` hỏng và `hasJoined` không
trả gì. Bên kiểm tra là **server hỏi thẳng Mojang**.

Với `online-mode=false` thì không có xác minh nào, ai cũng khai được tên bất kỳ —
Mojang ghi rõ trong `server.properties`. Rủi ro thật nằm ở phía vận hành: server
offline-mode phơi ra internet, hoặc proxy BungeeCord/Velocity đặt backend
offline-mode mà quên firewall backend (kết nối thẳng vào backend là bỏ qua toàn bộ
xác thực ở proxy). Lỗi trong bản thân Minecraft thì báo tại
<https://hackerone.com/minecraft>.

## Danh tính người chơi (liên kết Google)

Một ID riêng của launcher, **không suy ra từ UUID Minecraft nào**, nhóm nhiều tài
khoản Minecraft dưới cùng một người chơi.

Lý do tồn tại nằm ở một chi tiết dễ bỏ qua: UUID của hồ sơ offline sinh từ tên
người chơi, còn UUID premium do Mojang cấp — hai giá trị khác hẳn nhau. Nên mọi
thứ khoá theo UUID Minecraft đều **đứt gãy đúng lúc người chơi lên premium**.
`identity.py` sinh một `player_id` bằng `uuid4` thuần, cố tình không dính dáng gì
tới tên hay UUID, nên nó sống sót qua chuyển đổi đó.

```
Hồ sơ offline "Lan"     UUID 71880a3a…  ┐
                                        ├─ player_id af0a443f…  (không đổi)
Tài khoản premium LanMC UUID bbbbbbbb…  ┘
```

Liên kết Google chỉ là một *khoá ngoài* gắn vào danh tính, lưu theo claim `sub`
(ổn định kể cả khi người dùng đổi email). Đăng nhập bằng cùng tài khoản Google
trên máy khác thì nhận lại đúng danh tính thay vì đẻ ra bản sao.

Luồng đăng nhập theo chuẩn Google cho installed app: Authorization Code + PKCE,
redirect về `http://127.0.0.1:<cổng ngẫu nhiên>`, mở trình duyệt hệ thống chứ
không nhúng webview (Google chặn webview). Có kiểm `state` chống CSRF.

```bash
# console.cloud.google.com > Credentials > OAuth client ID > Desktop app
export GOOGLE_CLIENT_ID=<client-id>
export GOOGLE_CLIENT_SECRET=<secret>   # chỉ cần nếu Google cấp
```

Bấm tên tài khoản ở góc trên trái → **Liên kết tài khoản Google…**

**Phạm vi hiện tại là cục bộ.** `identity.json` nằm trên máy này. Muốn danh tính
theo người chơi sang máy khác thì cần một máy chủ giữ ánh xạ `sub → player_id`;
`identity.py` đã tách sẵn khoá ngoài ra khỏi ID nên chỗ đó cắm thêm được mà không
phải sửa mô hình dữ liệu.

## Dùng

```bash
python -m nostalgia account add                    # device code: mở link, nhập mã
python -m nostalgia account add --name Khach       # thêm người khác (demo nếu chưa mua)
python -m nostalgia account add-offline Lan        # hồ sơ offline (cần đã có chủ sở hữu)
python -m nostalgia account list                   # xem tất cả, * là mặc định
python -m nostalgia account default anh
python -m nostalgia account remove demo-2

python -m nostalgia versions --limit 10
python -m nostalgia fabric --list                  # phiên bản Fabric hỗ trợ
python -m nostalgia fabric 1.21.4                  # cài Fabric loader mới nhất
python -m nostalgia play 1.21.4                    # dùng tài khoản mặc định
python -m nostalgia play 1.21.4 --account anh --memory 4096
```

### Nhiều người dùng chung một máy

Mỗi người chạy `account add` một lần với tài khoản Microsoft của mình. Ai đã mua
thì vào full game, ai chưa mua thì vào demo — không cần cấu hình gì thêm, launcher
tự nhận qua kết quả `/minecraft/profile`.

```
   LABEL                LOẠI      CHẾ ĐỘ         TÊN TRONG GAME
 * jun                  msa       full game      JunMC
   anh                  msa       full game      AnhMC
   demo                 msa       demo           Khach1
   Lan                  offline   offline        Lan
```

Mỗi tài khoản Microsoft giữ refresh token riêng, nên đổi người chơi không phải
đăng nhập lại. Cột CHẾ ĐỘ hiện `offline->demo` nếu cổng sở hữu không còn thoả.

## Cấu trúc

| File | Việc |
|---|---|
| `auth.py` | Microsoft device code → Xbox Live → XSTS → Minecraft Services; phát hiện quyền sở hữu |
| `accounts.py` | `AccountStore` (thêm/xoá/đặt mặc định), `LaunchIdentity`, cache phiên (chmod 600), UUID offline v3 |
| `install.py` | Version manifest, client.jar, libraries, natives, assets; kiểm SHA1, tải song song |
| `launch.py` | Đánh giá `rules`, thay biến `${...}`, dò Java, chạy tiến trình |
| `__main__.py` | CLI |
| `ui/theme.py` | Bảng màu, font, gradient bóng/hắt, hàm blur |
| `ui/glass.py` | `GlassPanel` — nền mờ + sắc kính + bóng + viền vát |
| `ui/hero.py` | Ảnh nền voxel sinh bằng thuật toán |
| `ui/widgets.py` | Nút Aero, thanh tiến trình, mục sidebar, tab, icon vẽ tay |
| `ui/window.py` | Cửa sổ chính, ba tấm kính, bố cục |
| `ui/controls.py` | Danh sách cuộn, thanh trượt, công tắc |
| `ui/menus.py` | Menu kính thả xuống, phủ kín cửa sổ để bắt click ra ngoài |
| `ui/dialogs.py` | Hộp thoại kính: đăng nhập, nhập tên, xác nhận |
| `ui/pages.py` | Sáu trang nội dung |
| `ui/worker.py` | `QThread` cài + chạy game, tải nội dung, đăng nhập |
| `ui/app.py` | `Controller` — nối mọi nút vào hành động thật |
| `settings.py` | Cấu hình người dùng (RAM, thư mục, Java, phiên bản đang chọn) |
| `content.py` | Tin tức và ghi chú từ `launchercontent.mojang.com`, có cache |
| `fabric.py` | Fabric meta, dựng đường dẫn maven, trộn `inheritsFrom` |
| `doctor.py` | Chẩn đoán từng mắt xích, dùng để test launcher không cần tài khoản |
| `identity.py` | `player_id` ổn định, nhóm nhiều tài khoản, khoá ngoài OAuth |
| `google_auth.py` | OAuth Authorization Code + PKCE qua loopback |

Dữ liệu game mặc định nằm ở `~/.nostalgia-launcher`, tài khoản ở
`~/.config/nostalgia-launcher/accounts.json`.

## Đã kiểm tra

- UUID offline khớp giá trị vanilla (`Notch` → `b50ad385-829d-3141-a216-7e7d7539ba7f`)
- Dựng lệnh cho 1.8.9 / 1.16.5 / 1.21.4, cả hai chế độ, không sót placeholder `${...}`
- `--demo` bật đúng cho tài khoản chưa mua ở cả định dạng cũ (`minecraftArguments`)
  và mới (rule `is_demo_user`)
- Tải thật 1.8.9: 33 thư viện, 30 vào classpath, 6 natives giải nén đúng cho Linux
- `AccountStore`: thêm/xoá/đặt mặc định, tự đánh số label trùng (`demo`, `demo-2`),
  xoá tài khoản mặc định thì chuyển sang cái còn lại, state bền qua lần đọc lại,
  file lưu ở quyền 0600, đọc được cả định dạng JSON cũ
- Cổng sở hữu: chặn `add_offline` khi store rỗng và khi chỉ có tài khoản demo;
  mở khi có chủ sở hữu; xoá chủ sở hữu thì hồ sơ offline sinh ra lệnh có `--demo`
- `ensure_offline_libraries`: pass với 1.8.9 đã tải đủ, báo thiếu file với 1.21.4 chưa tải
- `doctor`: chạy đúng trên cả bản vanilla lẫn Fabric, bắt được Java thiếu, thư viện
  thiếu 70/78, asset index thiếu; hash khớp thì báo khớp; token bị che trong lệnh in
- Chạy song song: mở 3 instance cùng lúc, đếm đúng, cảnh báo dùng chung thư mục,
  dọn sạch khi thoát, nút CHƠI không bị khoá
- Fabric: trộn `inheritsFrom` cho 1.21.4, 121 thư viện gộp thành 78 jar trên
  classpath, thư viện loader đứng trước vanilla, jar dùng chung với bản gốc,
  tải thật 8 thư viện maven và SHA1 khớp
- Điều hướng: 4 tab và 3 mục sidebar đổi trang đúng, thanh dưới chỉ hiện ở tab Chơi
- Dữ liệu thật: 30 tin tức, 60 ghi chú, nội dung 7 378 ký tự, 80 phiên bản trong menu
- Lưu cấu hình xuống đĩa và đọc lại đúng; đổi tài khoản, xoá phiên bản, ba hộp thoại
- Đua tiến trình: chọn phiên bản thủ công không bị mặc định chạy nền ghi đè
- Danh tính: `player_id` giữ nguyên khi chuyển hồ sơ offline sang tài khoản premium
  (trong khi UUID Minecraft đổi hẳn), tra ngược từ nhãn và từ `sub`, đăng nhập lại
  cùng `sub` trên store khác thì nhận lại đúng danh tính chứ không tạo bản sao,
  file lưu quyền 0600
- Chạy thật trên X11/Cinnamon 1920×1080: cửa sổ canh giữa, kính và nút render đúng,
  trạng thái "Chưa đăng nhập" + chấm xám hiện đúng khi chưa có tài khoản nào
- GUI: `Controller` đọc đúng tài khoản mặc định từ `AccountStore` trên đĩa, nhãn và
  màu chấm đổi đúng khi xoá chủ sở hữu, thanh tiến trình ẩn lúc rảnh và hiện đúng
  tỷ lệ khi tải; ảnh chụp trong `docs/` render offscreen từ chính code này

## Chưa làm

- Forge (Fabric đã xong; Forge dùng installer jar riêng nên phức tạp hơn)
- Tự tải JRE theo `javaVersion` thay vì đòi máy cài sẵn
- Tải skin mới lên (trang Skin mới chỉ hiển thị)
- Tạo instance riêng với mod loader — cần Fabric/Forge trước
- Ảnh trong tin tức và ghi chú (mới hiện chữ)
- Máy chủ đồng bộ danh tính giữa nhiều máy (hiện chỉ lưu cục bộ)

## Ghi chú về cosmetic

Tôi không dựng phần cửa hàng hay ví cosmetic. EULA, mục USING mods, viết thẳng:
mod bạn tự làm thì thuộc về bạn *"as long as you don't sell them for money / try
to make money from them"*. Điều đó áp dụng cho mọi người mua, không phân biệt
premium hay không, nên đây là vấn đề của mô hình kinh doanh chứ không phải của
người chơi. Tầng danh tính ở trên vẫn dùng tốt cho việc quản lý nhiều tài khoản.

## Ghi chú

Launcher không tự vượt qua bước xác thực: người chưa mua game vào được demo,
không phải full game. Nếu bạn dựng server LAN riêng đặt `online-mode=false`,
`accounts.offline_uuid()` sinh đúng UUID mà server vanilla mong đợi — nhưng ở chế
độ đó server không xác minh danh tính, ai cũng mạo danh được ai, nên chỉ dùng sau
whitelist hoặc trong mạng kín.

## Giấy phép & cảm ơn

Phát hành theo **GNU General Public License v3.0** — bạn được tự do dùng, sửa và
chia sẻ, miễn là bản phái sinh cũng mở mã và giữ ghi công.

Cảm ơn [PrismLauncher](https://github.com/PrismLauncher/PrismLauncher) (GPL-3.0):
mô hình cổng chứng minh quyền sở hữu và cách sinh UUID offline trong dự án này
được tham khảo từ *hành vi* của Prism. Toàn bộ code ở đây viết lại độc lập bằng
Python, không sao chép mã nguồn của Prism.

Chuỗi xác thực Microsoft → Xbox Live → XSTS → Minecraft Services dựa trên tài liệu
giao thức công khai tại [minecraft.wiki](https://minecraft.wiki/w/Microsoft_authentication).
Không liên kết hay được xác nhận bởi Mojang/Microsoft.
