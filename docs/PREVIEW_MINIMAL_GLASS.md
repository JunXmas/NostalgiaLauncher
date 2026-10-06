# Preview UI: minimal + kính mờ

Mẫu riêng theo phản hồi của chủ dự án: UI đang rối về thứ bậc thị giác; cần màn hình đăng
nhập toàn cửa sổ, phong cách gọn như Modrinth, kính nhẹ, cuộn có quán tính như Skewlith
và giữ cách phối màu gốc của Nostalgia.

Chỉ chạy từ mã nguồn. Không thay `Main.qml`, không đổi bộ cài, không tạo tag, không build,
không push hoặc xuất bản release. Các file preview nằm trong `qml/preview/`.

## Mẫu để duyệt

- [Đăng nhập](preview/minimal/login.png): phủ toàn cửa sổ, mở maximized khi chạy lần đầu;
  Microsoft là lựa chọn chính, Ely.by và ngoại tuyến là lựa chọn phụ. Có đường khám phá
  trước; tài khoản có sẵn vào launcher ngay.
- [Trang chủ](preview/minimal/home.png): một nút Chơi chính; ưu tiên bản vừa chơi, sau đó
  bản ghim; các bản khác chỉ có nút chọn.
- [Bản chơi](preview/minimal/instances.png): bỏ ảnh rỗng lớn, giảm số nút nổi; quản lý/sao
  lưu/nhập vẫn truy cập được. [Dạng danh sách](preview/minimal/instances-compact.png).
- [Thư viện](preview/minimal/library.png): tìm kiếm và loại nội dung là hai lớp chính;
  bộ lọc nâng cao và Đã cài mở giao diện hiện có. [Các thẻ mod với nền mica từ avatar](preview/minimal/library-mods.png).
- Bấm thẻ để xem popup giữa cửa sổ: [mod](preview/minimal/project-mod.png),
  [resource pack](preview/minimal/project-resourcepack.png),
  [shader pack](preview/minimal/project-shader.png), [modpack](preview/minimal/project-modpack.png).
  Nút tải nhanh trên thẻ hoạt động riêng. [Danh sách bản phát hành](preview/minimal/project-mod-releases.png)
  và [popup ở cửa sổ nhỏ/chữ 150%](preview/minimal/project-small-150.png).
- [Video cuộn 5 giây](preview/minimal/scroll-preview.mp4): thao tác bánh xe thật trong Qt,
  có đổi hướng, quay về đầu và dừng dần; video ghi trước khi bổ sung mica cho thẻ.
- [Cửa sổ nhỏ, chữ 150%](preview/minimal/login-small-150.png) và
  [thư viện ở cùng kích thước](preview/minimal/library-small-150.png).

Ảnh chụp từ QQuickView chạy thật, 1440×900 và 1024×600. Tài khoản/bản chơi là dữ liệu mẫu
trong thư mục tạm. Danh sách và icon 12 modpack cùng 12 mod lấy từ API Modrinth, được nạp cục bộ khi
chụp; không phải bằng chứng cài hoặc chạy game. Nội dung/biểu tượng thuộc tác giả dự án.
Popup dùng giới thiệu và danh sách bản phát hành thật của Sodium, Fresh Animations,
Complementary Reimagined và Fabulously Optimized, nạp từ fixture cục bộ để chụp ổn định.

## Lựa chọn thiết kế

- Dùng lại palette trong `Theme.qml`: nền xám lạnh, Trang chủ xanh lá, Bản chơi vàng nâu,
  Thư viện tím, Tài khoản cyan, Chơi chung hồng, Nhật ký xanh dương và Cài đặt xám xanh.
  Màn đăng nhập dùng xanh thương hiệu. Chữ Inter, khoảng trống và độ đậm giữ bố cục gọn;
  nút chính lấy màu đậm của từng trang và chữ sáng như launcher gốc.
- Kính dùng ở thanh bên, khung đăng nhập, hero và popup dự án. Blur nền thật bằng MultiEffect trên
  OpenGL; có nền trong mờ dự phòng ở renderer phần mềm. Đây là kính mờ theo hướng liquid
  glass, chưa có khúc xạ vật lý kiểu thấu kính.
- Các thẻ Thư viện giữ avatar rõ phía trước và dùng cùng ảnh làm nền mica phía sau,
  theo kỹ thuật cũ: chồng hai ảnh thu nhỏ 4×4 và 7×7 rồi phóng mượt. Lớp phủ dùng màu
  nền gốc và tối hơn ở vùng chữ. OpenGL cắt nền theo góc bo; renderer phần mềm dùng nền
  thu vào trong góc, có chuyển sắc ở mép. Không có ảnh thì chỉ hiện icon dự phòng.
- Popup chung cho cả bốn loại nội dung: giới thiệu đầy đủ, chọn Minecraft, chọn bản phát
  hành (kèm release/beta/alpha và loader), rồi chọn bản chơi tương thích. Chọn Minecraft
  là lọc nội dung để cài; không đổi phiên bản game của bản chơi đã có. Nếu thiếu bản chơi,
  mở hộp tạo bản chơi hiện có và điền sẵn game/loader; đóng hộp đó trở lại popup.
  Modpack tạo bản chơi mới theo archive của đúng bản phát hành đã chọn, có ô đặt tên.
- Nền popup là mica xuyên thấu: lấy đúng vùng giao diện thư viện phía sau, blur và phủ
  màu nền cũ ở mức trong mờ, bo góc và thêm viền kính nhẹ. Nguồn thu không chứa popup/
  overlay để tránh hiệu ứng tự thu lại chính nó. Vùng thu bám vị trí khi mở và resize;
  dừng cập nhật khi đóng. Renderer phần mềm dùng lớp màu đậm hơn để giữ chữ dễ đọc.
- Popup cài đúng version ID; không rơi về bản mới nhất khi bản được chọn bị gỡ hoặc không
  tương thích. Có trạng thái tải, thử lại, tiến độ và kết quả cài; khóa thao tác cài lặp.
  Nội dung giới thiệu Markdown/HTML hiển thị thành văn bản cuộn được, có nút mở trang
  dự án gốc. CurseForge hiện dùng danh sách tối đa 50 file từ API như luồng thư viện cũ.
- Reuse BlockIcon và nguyên model/texture Minecraft; không vẽ lại beacon hoặc kệ sách.
- Cuộn bánh xe tích lũy đích, nội suy theo thời gian; đổi hướng liên tục và kẹp biên. Timer
  dừng khi hết chuyển động. Trackpad có pixel delta dùng quán tính của OS, tránh làm mượt
  hai lần. Bàn phím, kéo nội dung và scrollbar vẫn hoạt động. Giảm chuyển động tắt nội suy.

## Tham chiếu

- https://skewclient.store — đã mở bằng Chromium và đọc bundle JS/CSS. Website sử dụng
  Lenis với `lerp: 0.1`, `duration: 1.5`, `smoothWheel: true`; các panel dùng blur 14px.
  Preview Qt dùng suy giảm mũ tương đương lerp 0.1 ở 60fps, không chép nguyên hiệu ứng web.
- https://modrinth.com/app — phân cấp rõ, nền trung tính và thao tác chính có một màu nhấn.

Đây là phân tích tham chiếu cùng sở thích chủ dự án, chưa phải khảo sát người dùng.

## Chạy để xem

Khi môi trường source đã có PySide6:

```sh
.venv/bin/python bench/ui_minimal_preview.py
```

Mặc định dùng thư mục dữ liệu/config tạm; không đụng dữ liệu launcher đang sử dụng. Để
xem lại cùng tài khoản preview, dùng `--data-dir /path/to/preview-data`. Không tạo tài
khoản/mật khẩu mẫu trong source; form sử dụng các bridge đăng nhập hiện có.

## Kiểm chứng và giới hạn

- 31 kiểm tra UI liên quan (6 mới + preview controls, block models và block icons) qua
  renderer phần mềm. 6 kiểm tra mới cũng qua OpenGL/llvmpipe.
- 25 kiểm tra giao diện/QML và quy ước kiến trúc qua sau kiểm tra bổ sung.
- `ruff check` và mypy toàn kho qua. Sau đổi palette, 6 kiểm tra tương tác preview qua;
  ảnh và video được chụp lại trên OpenGL, không có cảnh báo QML.
- Sau thêm mica, 6 kiểm tra tương tác preview tiếp tục qua. Chụp mod/modpack, trường hợp
  thiếu avatar và cửa sổ 1024×600/chữ 150% trên OpenGL/llvmpipe và renderer phần mềm;
  cả hai không có cảnh báo QML. Đây là kiểm tra render, không đo hiệu năng GPU Windows.
- Sau thêm popup: 84 kiểm tra liên quan qua trên renderer phần mềm, gồm toàn bộ nhóm
  nội dung, bridge thư viện, preview, quy ước và kiến trúc. 14 kiểm tra tương tác/bridge
  preview cũng qua OpenGL/llvmpipe. Ruff và mypy (386 file) qua.
  Máy chủ HTTPS giả kiểm tra tải đúng bản cũ cho mod/resource pack/shader/modpack, giữ
  phụ thuộc mod, cập nhật/gỡ file cũ sau tải thành công, giữ file/sổ cũ khi tải lỗi, từ chối bản mất hoặc sai game/
  loader, và archive modpack có metadata game không khớp. Provider giả kiểm tra lỗi/
  thử lại, kết quả về muộn, chặn cài lặp và phân biệt bấm thẻ với nút tải nhanh.
- Sau thêm mica xuyên thấu, 10 kiểm tra preview/popup và 7 kiểm tra quy ước qua trên
  renderer phần mềm; 4 luồng popup qua trên OpenGL. Kiểm tra thêm vùng nền khớp vị trí
  popup trước/sau resize. Sáu ảnh popup được chụp lại trên OpenGL, không có cảnh báo QML.
- Thử đăng nhập ngoại tuyến thật qua bridge; Microsoft/2FA Ely.by dùng provider giả để
  kiểm tra luồng UI, hủy và xử lý lỗi; không đăng nhập tài khoản online thật.
- OpenGL được kiểm tra trên Linux/llvmpipe, chưa đo hiệu năng GPU Windows/macOS.
- Tài khoản, chơi chung, nhật ký, cài đặt và dialog quản lý nâng cao giữ UI hiện có. Các
  màn mẫu mới hiện dùng tiếng Việt; đồng bộ các màn còn lại và dịch mới sau duyệt hướng.

Chờ chủ dự án duyệt ảnh/chuyển động trước khi chuyển mẫu này thành UI mặc định hoặc build.
