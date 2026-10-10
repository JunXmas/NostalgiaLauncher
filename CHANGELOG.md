# Changelog

Mốc phát hành của Nostalgia Launcher. Phiên bản theo semver; tag `vX.Y.Z` kích hoạt
`.github/workflows/release.yml` (xem `docs/RELEASE.md`).

## Chưa phát hành

## 1.2.0rc26 — 2026-10-10

- Mở phòng theo ba bước rõ ràng: chọn bản chơi, mở world và bật LAN, rồi mời bạn.
  Launcher tự chuyển sang tab Chơi chung khi mở cửa sổ host; hướng dẫn LAN hiện
  ngay ở bước cần làm, không bắt nhập mã hoặc cổng khi tự nhận diện được.
- Hiện bạn trực tuyến và nút Mời chơi ngay trong bảng phòng, không cần chọn chat.
  Chỉ cho mời khi world và modpack đã sẵn sàng, phòng không khóa và lời mời trước
  đã gửi xong. Danh sách dài chỉ dựng các ô gần màn hình.
- Khách có nút Chép địa chỉ vào Minecraft ngay trong bảng phòng. Hướng dẫn có GIF,
  Tiếng Việt và English được cập nhật theo đúng các nút mới.
- Giảm làm mới danh sách bạn bè khi không mở chat từ 20 xuống 4 lần mỗi phút;
  không tải tin nhắn ở nền khi rời trang. Mở lại trang làm mới ngay, chat cập nhật
  mỗi 5 giây và thao tác gửi tin/gửi lời mời vẫn xử lý ngay.
- Backend đã giảm ghi trạng thái online lặp lại, giữ kiểm tra phiên đăng nhập,
  chữ ký chống phát lại và quyền Premium trên máy chủ.
- Sửa callback nền mica gọi vào ô thư viện đã đóng khi chuyển loại nội dung;
  giữ nền blur cho mod, modpack, shader và resourcepack.

## 1.2.0rc25 — 2026-10-10

- Đóng dịch vụ phòng nhiều lần an toàn, không tạo coroutine sau khi vòng lặp đã đóng;
  bộ test thu hồi cửa sổ/worker Qt sau từng test để tránh ảnh hưởng giữa các màn hình.

- Sửa lỗi vòng đời bộ lọc kéo thả Qt có thể làm các màn hình skin, tạo bản chơi,
  xác nhận xóa hoặc trang chủ lỗi khi mở cửa sổ mới.

- Sửa gửi/nhận/từ chối lời mời world bị khóa bởi polling bạn bè. Chặn thao tác
  trùng, giữ điều kiện LAN/modpack sẵn sàng và không vào phòng từ phiên tài khoản cũ.
- Thêm hướng dẫn Mời bạn vào world bằng Tiếng Việt/English với GIF: host mở LAN,
  gửi lời mời, khách nhận/đồng bộ pack và kết nối trong Minecraft. Hiện sẵn lời mời đến.
- Bỏ tự ẩn launcher khi Minecraft khởi chạy, kể cả cấu hình cũ đã bật; giữ chat,
  lời mời và phòng kết nối. Không giành tiêu điểm khi người chơi tự thu nhỏ cửa sổ.
- Thư viện tổng mở chọn bản chơi và phiên bản trước khi cài mod, shader hoặc
  resourcepack; không tự cài vào đích đã chọn trước đó. Sửa nhãn Install bị dịch
  thành Settings. Thư viện trong bản chơi giữ đích cài cố định.
- Nút Chấp nhận kết bạn không bị khóa bởi cập nhật danh sách ở nền; thao tác
  kết bạn chạy riêng, chặn gửi lặp và bỏ kết quả của phiên cũ. Hiện sẵn yêu cầu đến.
- Chặn click xuyên popup/menu: mỗi lần bấm chỉ kích hoạt nút đang hiển thị;
  menu tài khoản và chọn phiên bản chặn thao tác ở nền, giữ kéo cuộn bình thường.
- Sửa vệt trắng ở hướng dẫn và ô thư viện khi ảnh chưa tải hoặc blur tắt:
  mask chỉ dùng để cắt hiệu ứng, không xuất hiện trên giao diện.
- Sửa lưới thư viện, bản chơi và cosmetic xuống dòng sớm, để trống cột;
  hướng dẫn chuyển bố cục theo chiều rộng và cỡ chữ để nội dung không chồng nhau.

## 1.2.0rc19 — 2026-10-10

- Sửa mở phòng/chia sẻ NeoForge bị báo không tìm thấy phiên bản loader dù đã cài:
  đọc phiên bản NeoForge từ metadata khởi động chính thức, không nhầm số hiệu FML.
  Áp dụng cho đồng bộ phòng, xuất modpack và kiểm tra mod; không cần cài lại loader.
  Nhận đúng nhánh NeoForge của Minecraft 26.x khi cài cho máy khách.
- Cuộn thư viện và danh sách dài nhẹ hơn: chỉ dựng ô gần màn hình, tái sử dụng ô khi
  cuộn; áp dụng cho mod/modpack/shader/resource pack, bản chơi, nội dung đã cài, server,
  sửa mod, nhập bản chơi, bạn bè, chat, cosmetic và danh sách đồng bộ.
- Giảm chi phí nền mica bằng ảnh blur nhỏ và capture tĩnh; cập nhật ảnh đúng khi ô được
  tái sử dụng, giữ blur cho popup. Bật/tắt mod giữ vị trí cuộn và trạng thái xác nhận gỡ
  được đặt lại khi chuyển sang file khác.
- Chat dùng được ngay sau khi kết bạn, kể cả bạn ngoại tuyến; đồng bộ tài khoản không
  khóa nút Gửi. Giữ bản nháp khi gửi thất bại và xử lý phiên bị thu hồi.
- Trang quản trị riêng có mục **Số liệu launcher**: hoạt động tài khoản Google theo
  ngày/tuần/tháng, số phiên trực tuyến và lượt tải GitHub theo nền tảng/bản phát hành.
  Thống kê ngày tính theo giờ Việt Nam, bắt đầu từ khi triển khai bộ thu thập.

- Hoàn thiện giao diện **Tiếng Việt / English**: trang chính, tài khoản và skin/cape,
  thư viện, quản lý bản chơi, bạn bè/đồng bộ, server, cosmetic, Premium và cập nhật.
- Chọn ngôn ngữ ngay trên màn hình đăng nhập hoặc trong Cài đặt; áp dụng ngay cho
  cửa sổ đang mở, hướng dẫn và menu khay hệ thống, lưu cho lần khởi động sau.
- Dịch trạng thái và lỗi do launcher tạo, giữ tên người chơi, phiên bản, đường dẫn và
  log gốc. Định dạng số theo ngôn ngữ; giữ tiền thanh toán là VND.
- Chỉnh khoảng cách màn hình đăng nhập khi cửa sổ nhỏ và cỡ chữ 150%; thêm kiểm tra
  bản dịch, tham số câu, chuyển ngôn ngữ và hướng dẫn bảo trì bộ ngôn ngữ.

## 1.2.0rc18 — 2026-10-09

- Nhận đúng phiên bản Forge hiện đại từ `net.minecraftforge:fmlloader`, khắc phục
  lỗi yêu cầu cài lại loader khi host/chia sẻ modpack đã chạy được. Xuất modpack và
  quét sửa mod cũng dùng cùng cách nhận diện; không nhầm phiên bản FML độc lập của
  NeoForge hay các mod trùng tên loader.

- Thay **Sao lưu** bằng **Xuất modpack**: chọn bản chơi, MRPACK Modrinth hoặc ZIP
  modpack CurseForge, nơi lưu và tùy chọn kèm thế giới. Giữ mods đang tắt, resourcepack,
  shader, cấu hình và đúng Minecraft/loader. File xuất có thể nhập lại qua Nhập bản chơi.
- **Xóa vĩnh viễn** có xác nhận: xóa dữ liệu bản chơi được launcher quản lý, không chuyển
  qua thùng rác. Thư mục game riêng chỉ xóa khi bật lựa chọn tương ứng và xác nhận đường
  dẫn; chặn thư mục chứa kho launcher hoặc được bản chơi khác sử dụng.
- Bản sao lưu/thùng rác cũ vẫn có thể khôi phục qua **Khôi phục dữ liệu cũ**. Thêm nút
  xóa hẳn từng bản chơi trong thùng rác cũ; giữ các file đã xuất độc lập với bản chơi.
- Xuất chạy ở nền, ghi file nguyên tử, giữ file đích cũ khi thất bại và chặn liên kết,
  tên file trùng khi đổi hệ điều hành hoặc dữ liệu thay đổi trong lúc đóng gói. Nhập
  overrides theo từng khối để không nạp cả thế giới lớn vào RAM. Cập nhật GIF hướng dẫn.

## 1.2.0rc17 — 2026-10-09

Kết quả worker được giao tới UI trước khi báo rảnh; tác vụ cũ không làm tác vụ mới mất
trạng thái bận. Tránh bỏ kết quả tải phiên bản server và checkout ở yêu cầu nối tiếp.

Yêu cầu đọc lại tài khoản Google trong lúc worker bận được thực hiện ngay khi worker
xong, thay vì đợi chu kỳ tiếp theo. Đăng xuất/hủy phiên hủy cả yêu cầu đang chờ.

Skin/cape có bản xem trước riêng theo tài khoản và nút Lưu; Classic/Slim đổi model ngay.
Sửa mod chỉ đọc bằng chứng lỗi trong log, không biến cảnh báo metadata thành lỗi game.
Cuộn Nhật ký giữ biên ổn định. Khôi phục icon, sửa nhãn Premium bị tràn, canh mũi tên tài
khoản, đưa đăng xuất Google về nơi dễ tìm và dùng khối amethyst cho Cosmetic. Quyền host
server được kiểm tra tự động. Giữ luồng cập nhật cũ: tự kiểm khi mở, chỉ tải/cài sau khi
người chơi bấm Cập nhật ngay. Gói phát hành không mở quyền Ultimate thử nghiệm.

### Thêm nội dung ngay từ quản lý bản chơi

Trong **Nội dung đã cài**, nút **Thêm nội dung** mở chính thư viện của launcher với
Mod, Shader và Gói tài nguyên. Minecraft, loader và bản chơi đích được lọc sẵn;
popup dự án chỉ cho cài phiên bản phù hợp vào bản chơi đang quản lý. Shader và
gói tài nguyên lọc theo Minecraft, không bị ghim nhầm vào loader của mod.

Bấm **Quay lại quản lý** để xem danh sách đã cài được cập nhật; tên, cấu hình đang
sửa vẫn được giữ. Thư viện chính vẫn dành cho khám phá toàn bộ kho và tạo bản chơi
từ modpack. Không thay đổi nội dung khi Minecraft đang chạy hoặc bản chơi đang bận.

### Hướng dẫn ngay tại thao tác, kéo thả mod vào đúng bản chơi

Không cần đoán cách dùng: nút **Cách dùng** và phím **F1** mở hướng dẫn cho mục đang
xem, với GIF quay từ launcher, các bước ngắn và lưu ý thực tế. Có 17 chủ đề, từ tài
khoản, skin/cape đến đồng bộ pack và server. Popup mica giữ nguyên biểu mẫu bên
dưới; đóng trợ giúp trở về thao tác đang làm. GIF dùng ngoại tuyến, chỉ nạp khi mở
và dừng khi ẩn cửa sổ hoặc bật giảm chuyển động.

Kéo một hoặc nhiều file mod `.jar` vào bất kỳ trang hay popup nào để chọn bản chơi
đích. Chỉ cài sau khi xác nhận, giữ nguyên file gốc và chặn ghi khi Minecraft đang
chạy. File trùng tên mặc định được bỏ qua; bật thay thế sẽ giữ bản cũ để khôi phục
và giữ mod đang tắt ở trạng thái tắt. Nếu chép lỗi, launcher hoàn tác phần đã ghi.

### Đổi giấy phép: AGPL-3.0 → PolyForm Strict 1.0.0

Mã nguồn vẫn công khai để ai cũng đọc và tự kiểm launcher có an toàn không, nhưng không còn
là mã nguồn mở: cấm dùng thương mại, cấm phân phối lại, cấm phát tán bản sửa đổi. `NOTICE`
cho thêm quyền sửa trên máy riêng để kiểm thử và gửi pull request về dự án. Các bản tới và gồm
1.1.7 đã phát hành theo AGPL-3.0 và giữ nguyên giấy phép đó.

## 1.1.7 — 2026-10-05

### Windows: "không gọi được https://cdn.modrinth.com/..." khi tạo bản chơi từ modpack — đã sửa

Trên Windows 10 lâu không cập nhật, tải từ cdn.modrinth.com hỏng sau 4 lần thử trong khi
`curl.exe` tới cùng địa chỉ vẫn được. `ssl.create_default_context()` chỉ chép những root
đang nằm sẵn trong kho chứng chỉ Windows vào OpenSSL, còn Windows tải root thiếu từ Windows
Update đúng lúc Schannel cần — nên curl (Schannel) qua được mà launcher thì không. Launcher
giờ xác minh bằng bộ xác minh của hệ điều hành qua `truststore` (đi kèm extra `ui`, tức gói
phát hành); thiếu `truststore` thì lõi vẫn dùng `ssl` chuẩn như cũ. Context mặc định chuyển
sang `net/tls.py`.

## 1.1.3 — 2026-09-29

### Windows: bấm cập nhật xong app không mở lại nữa — đã sửa

Trên Windows, bấm **Cập nhật** làm launcher tắt rồi không bao giờ mở lại. Nguyên nhân: khi
spawn script tráo, launcher không truyền `cwd=`, nên script kế thừa thư mục làm việc của
launcher — mà lối tắt do Inno Setup tạo **không đặt `WorkingDir`**, nên Windows lấy mặc định
là chính **thư mục cài**. Windows giữ handle chặn DELETE trên thư mục làm việc của mọi tiến
trình đang sống, và đổi tên một thư mục cần quyền DELETE. Script tự khoá đúng thứ nó định
dời: `Move-Item` ném "Access to the path is denied" cả 30 lần thử rồi `exit 1` — sau khi
launcher đã `os._exit(0)`. Không còn ai mở lại nó.

Ba lớp vá: launcher truyền `cwd=%TEMP%` khi spawn (Linux cũng vậy, vì script `rm -rf` chính
thư mục cài); script tự ra `%TEMP%` **trước** mọi `Move-Item`, phòng trường hợp chạy tay; và
`Start-Process` mở lại launcher với `-WorkingDirectory` trỏ thẳng thư mục cài mới thay vì để
nó kế thừa `%TEMP%`.

Lớp thứ hai cần **hai** lệnh, không phải một: `Set-Location` chỉ đổi "current location" của
provider PowerShell (thứ `$PWD` trả về), không đổi thư mục làm việc thật của tiến trình ở mức
Win32 — mà handle khoá DELETE nằm đúng ở mức Win32 đó. Phải gọi thêm
`[System.IO.Directory]::SetCurrentDirectory`. Bản vá đầu chỉ có `Set-Location` và **CI trên
Windows thật đỏ** với `Move-Item` vẫn "Access denied"; máy dev Linux không cách nào nói ra
được điều đó. Có gác riêng cho dòng này.

Và hai lớp bọc ngoài, vì cwd chỉ là MỘT lối làm move hỏng — Defender giữ file, ổ đầy, thư
mục đang mở trong Explorer đều cho ra đúng cảnh "tắt rồi không mở lại" nếu script bỏ đi im
lặng:

- **Hỏng gì cũng mở lại launcher.** Move hỏng thì thư mục cài chưa bị đụng — mở bản cũ lên;
  chép hỏng thì trả lại bản cũ rồi mở nó lên. Người dùng mất bản cập nhật là chuyện nhỏ, mất
  launcher là chuyện lớn. Chỉ hai đường được phép không mở: launcher cũ không chịu thoát
  (mở thêm là hai bản tranh nhau ghi dữ liệu), và đường hỏng-nặng không trả lại được bản cũ
  (nhật ký ghi rõ thư mục `.old` nằm đâu để cứu tay). Có test gác từng đường.
- **Lối tắt của bộ cài đặt `WorkingDir` ra ngoài thư mục cài** (`installer.iss`) — bịt
  nguyên nhân ở gốc: launcher không bao giờ chạy với thư mục làm việc trỏ vào thư mục cài
  nữa. Launcher không dùng đường dẫn tương đối nào (đã rà: mọi `open()` đều trên đường tuyệt
  đối, game chạy với `cwd=game_dir`) nên đổi vô hại.

Bản Linux **không đổi** — jun xác nhận tự cập nhật trên Linux chạy đúng, và đổi một đường
đang chạy được không có ai báo lỗi chỉ là thêm chỗ để hỏng.

Vì sao lỗi này sống qua nhiều bản: script chạy **sau** khi launcher thoát với stdout/stderr
đổ vào `DEVNULL`, nên hỏng là hỏng câm và mỗi lần sửa đều là đoán từ triệu chứng. Nay script
ghi nhật ký cạnh chính nó (`apply-update.log`) — có bước hỏng và câu lỗi thật. Test tái hiện
bằng cách spawn script với `cwd` trong thư mục cài; nó **chỉ chạy trên Windows**, vì Linux
không khoá thư mục theo cwd nên chạy ở máy dev là tự lừa mình — job `check-windows-updater`
trong `ci.yml` là chỗ nó thực sự gác.

### Ô CỘNG ĐỒNG trên thanh bên

Thanh bên có thêm một ô dẫn thẳng tới máy chủ Discord của Nostalgia. Trước đó địa chỉ ấy
không nằm ở đâu trong launcher — người chơi muốn hỏi một câu phải tự đi tìm.

Ô nằm **dưới vạch ngăn**, tách khỏi bảy mục trên nó, và không sáng lên khi bấm: bảy mục kia
đổi trang bên phải, ô này mở trình duyệt rồi người dùng vẫn đứng nguyên ở trang cũ. Hai loại
hành vi khác nhau thì phải nhìn ra được *trước* khi bấm.

Địa chỉ để ở `repo/endpoints.py` cạnh mọi địa chỉ khác, nên đổi lời mời chỉ phải sửa một
dòng. Bản điện thoại dùng đúng link đó, ở mục CỘNG ĐỒNG trên rail dọc.

## 1.1.2 — 2026-09-29

Ba lỗi trong THƯ VIỆN, tất cả đến từ một phản hồi của người chơi: "cài modpack không thấy
được hết mọi thứ, mà phần lọc phiên bản thì vướng".

### Modpack không còn bị ghim vào phiên bản của bản chơi đang chọn

Chọn bản chơi xong thì bộ lọc nhảy về loader + phiên bản của bản chơi đó — hợp lý cho mod
và shader, nhưng **sai hoàn toàn với modpack**: modpack *tạo ra* một bản chơi mới chứ không
cài vào bản nào. Hậu quả là pack 1.7.10 bị giấu chỉ vì bản chơi đang chọn là 1.21, và người
chơi tưởng kho chỉ có vài chục pack.

Nay đổi chip loại thì bộ lọc mặc định tính lại theo loại đó, và modpack thì không lọc gì.
Bộ lọc người dùng **tự** tick vẫn giữ nguyên khi đổi chip — chỉ bộ lọc mặc định mới bị đặt lại.

### Danh mục phiên bản không còn bị cắt còn 60 mục

Cột lọc cũ cắt danh mục Mojang (hơn 500 bản) xuống 60 cho vừa bề ngang cột, và không nói gì.
Ai tìm bản cũ thì gõ mãi không ra. Khay mới cuộn được nên giữ nguyên cả danh mục.

### Cột lọc dọc thành ba ô ngang thu gọn

Cột trái 210px trải thẳng 4 loader cộng hàng chục phiên bản theo chiều dọc, đẩy phần **Sắp
xếp** ra khỏi tầm mắt. Nay là ba ô cùng một dòng — **Mọi loader** / **Mọi phiên bản** /
**Liên quan** — bấm mới bung khay, bấm ra ngoài thì đóng.

- Ô đóng vẫn nói được đang lọc gì: một mục thì hiện tên nó, nhiều mục thì `1.21.4 +2`.
- Dấu **✕** ngay trên ô xoá cả nhóm, không phải bỏ tick từng mục.
- Khay phiên bản có ô tìm riêng.
- Bỏ cột nên phần kết quả rộng thêm 234px, và số cột thẻ tính theo bề ngang thật thay vì
  ghim cứng hai cột.

### Nút Ủng hộ dự án trong CÀI ĐẶT

Launcher miễn phí, không quảng cáo. Nút nằm im ở hàng "Phiên bản launcher" — không popup,
không nhắc theo lịch, không chặn tính năng nào.

## 1.1.1 — 2026-09-26

Ba lỗi được vá và một tính năng cũ quay lại.

### CHƠI CHUNG vào được phòng thật sự

World của bạn hiện trong tab LAN nhưng bấm vào là "Connection Refused". Minecraft nối tới
`<IP nguồn beacon>:<cổng>` — nguồn multicast là IP card LAN (192.168.x) — còn proxy của
launcher chỉ nghe 127.0.0.1 nên từ chối đúng kết nối nó tồn tại để phục vụ. Mọi test cũ nối
thẳng loopback nên xanh hết; chỉ máy thật mới lộ. Proxy nay nghe mọi interface IPv4 nhưng
**đóng ngay mọi kết nối không phải từ chính máy này** (luật bảo mật L7 dạng mới), và đã kiểm
trọn vòng beacon → IP LAN → relay thật → world trên máy thật.

### Tự cập nhật trên Windows chạy lại được

Người dùng 1.0.15 Windows báo launcher không tự lên bản mới. Script tráo thư mục là
batch chạy qua `cmd.exe`, và nó chết hoàn toàn im lặng theo ba đường cùng lúc:
`timeout /t` thoát ngay khi stdin bị redirect (vòng chờ không ngủ giây nào), `cmd.exe`
đọc script theo OEM codepage (tên người dùng có dấu tiếng Việt là đường dẫn thành rác),
và `move` không thử lại khi Defender còn giữ file exe vài giây sau khi launcher thoát.

- Script tráo nay là **PowerShell** (sẵn trên mọi Windows 10/11): ghi UTF-8 có BOM,
  chờ PID có deadline, move thử lại 30 lần, chép hỏng thì trả lại thư mục cũ.
- CI thêm job chạy test bộ tự cập nhật **trên Windows thật** — bug này sống sót được
  vì mọi test Windows đều bị skip trên máy dev Linux.
- **Người dùng 1.0.15–1.1.0 trên Windows cần cài tay bản này một lần** (tải
  `setup.exe` hoặc `.zip` ở trang release) — bộ tự cập nhật của bản cũ chính là thứ
  bị hỏng. Từ 1.1.1 trở đi tự cập nhật chạy bình thường.

### Thẻ hành tinh quay lại — khi thanh bên thu gọn

Thanh bên có nút **THU GỌN**: gọn còn cột icon, và ở trang chủ sáu mục điều hướng
bay ra thành sáu thẻ neo vào các hành tinh trong ảnh nền. Rê chuột là thẻ nhấc lên
và **hành tinh sáng quầng**. Mở thanh bên lại thì thẻ nhường chỗ — không lúc nào có
hai đường đi trùng nhau (lý do bộ thẻ cũ bị bỏ ở 1.0.14).

### Nút "Dùng" không bao giờ hiện nếu hai tài khoản trùng tên

(ví dụ một Microsoft và một Ely.by cùng tên "JunSlayest").

- **Danh tính tài khoản khoá theo `account_id` (`kind:uuid`)**, không theo tên nữa. Trước
  đây hai hàng trùng tên đều tự nhận là hàng "đang dùng", mà nút Dùng chỉ hiện ở hàng
  *không* phải hàng đang dùng — nên nó trong suốt ở mọi hàng, mọi lúc.
- **Bấm Dùng chạy đúng tài khoản đó.** `find_account` khớp `account_id` trước, tên sau;
  trước đây tra theo tên và trả về cái đầu tiên, nên bấm Dùng ở hàng Ely.by vẫn chạy game
  bằng tài khoản Microsoft. CLI `--account Jun` gõ tay vẫn dùng được như cũ.
- **Xoá tài khoản chỉ gỡ đúng một.** Trước đây gỡ mọi hàng trùng tên — xoá tài khoản Ely.by
  làm mất luôn vé đăng nhập Microsoft.

## 1.1.0 — 2026-09-26

Một đợt làm lại giao diện. Bảy trang trước đây nhìn như một trang; giờ mỗi tab có sắc riêng,
chữ dùng font đóng kèm, và các thẻ nổi lên thay vì nằm phẳng.

- **Mỗi tab một màu.** Trước chỉ một sắc lục dùng ở 94 chỗ. Nay bảy sắc lấy từ chính khối
  icon của mục đó, nền pha 6% màu tab và chuyển mượt khi đổi trang. Hai màu phải dịch khỏi
  tông gốc vì va nghĩa: CÀI ĐẶT (đá đỏ trùng màu báo lỗi) và CHƠI CHUNG (ngả đỏ cạnh màu
  báo lỗi).
- **Font đóng kèm, hình khối vuông.** Inter cho chữ đọc + Minecraft F2D cho nhãn viết hoa
  (SIL OFL 1.1, cả hai đo được phủ đủ 74 ký tự có dấu tiếng Việt). Bo góc về 0 và thẻ vẽ
  bằng cạnh vát — đo trên chính CSS của minecraft.net. Gom 221 chỗ viết tay cỡ chữ thành
  5 bậc.
- **Icon khối Minecraft xoay** khi rê chuột ở thanh bên: tăng tốc dần, rung từng cơn, rời
  chuột thì hãm rồi quay về đúng khung 0. Texture lấy từ jar client của chính bạn (chỉ đọc);
  không có jar thì vẽ bằng code. Lúc rảnh tốn 0,0% CPU.
- **Thẻ bản chơi nổi lên**: nét mực 2 px, cạnh dưới dày, ô ảnh khoét lõm vào mặt thẻ, trỏ
  vào thì nhấc lên 3 px.
- **Thanh bên vẽ đầu nhân vật từ skin** thay vì một chữ cái trên nền màu.
- **TẠO BẢN CHƠI gọn lại**: bản "Tối ưu hiệu năng" là thẻ riêng có chip ĐỀ XUẤT và chọn sẵn;
  năm loader kia vẫn hiện đủ; chỉ RAM và thư mục gập vào "nâng cao". Chọn bản không hỗ trợ
  thì **không còn bị xoá ngầm lựa chọn** — nút tạo bị chặn kèm dòng nói thiếu gì và một nút
  thoát ngõ cụt.
- **Trang chủ bỏ sáu thẻ trùng đường đi** với thanh bên (và che mất ảnh nền). Chưa có tài
  khoản hoặc bản chơi thì khối CHƠI nói thiếu gì và đưa luôn nút đi làm việc đó, thay vì một
  nút xám câm.

### Tài khoản & skin Ely.by

- **Tải sẵn hỗ trợ skin ngay lúc đăng nhập Ely.by**, không đợi tới lúc bấm CHƠI. Hàng tài
  khoản nói "Skin trong game: đang tải hỗ trợ…" khi chưa xong. Lỗi mạng thì mất skin chứ
  không mất buổi chơi.
- **Nút Dùng để chuyển tài khoản** trên mọi hàng chưa chọn. Trước đây bấm cả hàng vẫn chuyển
  được nhưng không có gì nói ra điều đó.
- **Hai đường ra ely.by**: "Đăng ký ↗" cạnh nút đăng nhập, và "Đổi skin ở ely.by ↗" cho tài
  khoản Ely — launcher không có API upload skin cho họ, nên "Thêm skin" chỉ đổi ảnh launcher
  hiện, người chơi khác trong game vẫn thấy skin cũ.
- Sửa: nút "Thêm skin" tràn 16 px ra ngoài ô Skin.
- Sửa: bấm DỪNG lúc tắt "ẩn khi chơi" thì cửa sổ tự thu nhỏ.

### Giấy phép

- **GPL-3.0 → AGPL-3.0.** Điều 13 của AGPL buộc ai chạy bản đã sửa cho người khác dùng qua
  mạng cũng phải mở mã. Kho có relay chơi chung — chỗ đó nếu chỉ GPL thì một fork đóng mã
  chạy trên máy chủ được mà không vi phạm gì.
- Phần máy chủ tách sang kho riêng. Mọi dòng chạy trên máy bạn vẫn công khai: gỡ gói ra là
  đọc được, nên đóng nó chỉ mất lòng tin mà không bảo vệ được gì.

## 1.0.15 — 2026-09-23

- **Dải báo bản mới ở đầu cửa sổ**, thấy ở mọi trang, kèm phần trăm lúc tải. Trước đây nút
  tải chỉ nằm trong CÀI ĐẶT → CẬP NHẬT nên gần như không ai thấy. Đóng được bằng ✕; đóng rồi
  thì im tới lần mở launcher sau.
- **Cập nhật chỉ còn một nút.** Bấm "Cập nhật ngay" là launcher tải, tự cài, tự tắt và mở
  lại — không phải bấm lần thứ hai. Bản macOS `.app` và bản chạy từ mã nguồn không tự cài
  được thì mở thẳng trang tải, thay vì tải một gói rồi mới báo lỗi.
- **Bản AppImage và bản `.deb`/`.rpm` giờ cũng tự cập nhật được.** Launcher tải đúng loại gói
  hệ thống của bạn (không còn tải `.zip` rồi mới báo không cài được): AppImage thay thẳng file
  đang chạy, `.deb`/`.rpm` nhờ trình quản lý gói cài đè qua một hộp thoại xin mật khẩu của hệ
  điều hành. Mọi gói đều phải khớp `SHA256SUMS` mới được cài. Máy không có `pkexec` hay bạn bấm
  Huỷ thì launcher nói rõ, không âm thầm coi như đã cập nhật.

## 1.0.14 — 2026-09-21

Gộp 11 bản vá. Ghi chú đầy đủ: [release v1.0.14](https://github.com/JunXmas/NostalgiaLauncher/releases/tag/v1.0.14).

- **Chơi chung**: dò "Open to LAN" nghe trên từng card mạng một (máy nhiều NIC / VPN trước đây
  bị trượt); cổng bị chiếm và "chưa ai mở LAN" báo hai câu khác nhau; chống spam vào phòng ở
  relay đã thực sự được gọi.
- **Skin**: Ely.by hết luôn ra Steve/Alex (launcher gọi `http://` rồi tự từ chối chính mình);
  đổi skin Microsoft kiểm kích thước ảnh + làm mới phiên; skin tự chọn không bị đồng bộ ghi đè.
- **Nhập bản chơi**: thêm TLauncher và SKlauncher (tổng 6 launcher); vá ModrinthApp quét rỗng
  vì thiếu đường Flatpak.
- **Tự cập nhật**: AppImage và thư mục cài chỉ-đọc báo rõ thay vì tráo hỏng.
- **Windows**: cài Forge và tự cập nhật không còn bật cửa sổ CMD đen; Discord Rich Presence
  chạy được (trước là chỗ trống).
- **Giao diện**: thanh chọn bản chơi mở sẵn bản vừa chơi; nút gạt vẽ lại kiểu Bedrock.

## 1.0.13 — 2026-09-17

- **Minecraft không còn mở kèm cửa sổ CMD trên Windows.** Java chạy với `CREATE_NO_WINDOW`,
  đóng nhầm cửa sổ console không làm Minecraft tắt theo.
- Dọn nút nhập modpack và wrapper trùng lặp; thống nhất tên tham số `display_label`.

## 1.0.12 — 2026-09-17

Bản vá khẩn cấp, gộp cả 1.0.11 (bản đó dựng xong nhưng chưa từng phát hành).

- **Bản chơi không còn mang tên file thay vì tên pack** — nhập modpack để trống ô tên thì lấy
  tên thật trong `modrinth.index.json`.
- **Chọn nhầm file không còn im lặng** — lỗi nhập từ file hiện trên dải báo lỗi.
- **Sửa `Exception occurred in preexec_fn`** khi tự cập nhật trên Linux: launcher đã là session
  leader thì `os.setsid()` ném *Operation not permitted*. Thay bằng `start_new_session=True`.
- **"Chọn ổ khác" không còn im lặng** khi đường dẫn không hợp lệ.

## 1.0.6 — 2026-09-14

Bản vá khẩn cấp:

- **Sửa lỗi cài `.deb` trên Linux Mint** (MYLA-19) — `.deb` trước dùng nén zstd mà `dpkg`/`apt`
  trên Mint và Ubuntu cũ chưa hỗ trợ. Chuyển sang xz.
- **Sửa giao diện trên màn hình nhỏ** (MYLA-20) — ở 1366×768 nút bị chèn lên nhau hoặc biến
  mất. Giảm cỡ cửa sổ tối thiểu, thêm ScrollView, layout co giãn từ 1024×768 trở lên.

## 1.0.5 — 2026-09-13

Bản vá khẩn cấp: tự cập nhật tải xong nhưng không áp được, trên cả ba hệ.

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
