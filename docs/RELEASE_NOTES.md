# Nostalgia 1.2 — Diện mạo mới. Chơi cùng nhau.

Một launcher quen thuộc, được làm mới từ cách nhìn đến cách chơi. Nostalgia 1.2 giữ hệ màu của Nostalgia, đưa chất liệu kính vào giao diện, và giúp bạn cùng bạn bè bước vào một thế giới với ít thao tác hơn.

**Nostalgia 1.2.0rc16 tiếp tục hoàn thiện diện mạo mới trước bản ổn định 1.2.** Đăng nhập Google và Plus kết nối dịch vụ thật; quyền trả phí được xác nhận từ tài khoản, không mở khóa mô phỏng như draft Ultimate TEST trước đây.

## Mới trong rc16 — Ít đoán hơn, dễ chơi hơn

- **Thêm nội dung ngay trong bản chơi:** từ Quản lý → Nội dung đã cài → Thêm nội dung, mở kho Mod, Shader và Gói tài nguyên với Minecraft, loader và bản chơi đích được lọc sẵn. Chỉ cài bản tương thích vào đúng instance; quay lại quản lý vẫn giữ tên và cấu hình đang sửa. Kho chính vẫn dành cho khám phá và tạo instance từ modpack.
- **17 hướng dẫn ngay tại thao tác:** nút Cách dùng và phím F1 mở các bước ngắn kèm GIF từ launcher. GIF chạy ngoại tuyến, chỉ nạp khi cần và dừng khi ẩn cửa sổ hoặc giảm chuyển động. Đóng hướng dẫn để tiếp tục đúng biểu mẫu đang làm.
- **Kéo thả mod từ bất kỳ trang hay popup nào:** chọn một hoặc nhiều JAR rồi chọn instance đích, xác nhận trước khi cài. Giữ file gốc, mặc định bỏ qua file trùng tên; khi thay thế có bản sao lưu, giữ trạng thái mod đã tắt và hoàn tác nếu chép lỗi. Chặn cài khi Minecraft đang chạy.
- **Skin và cape: xem trước rồi mới Lưu.** Công tắc Classic/Slim thay model trực tiếp; cape được mặc trên nhân vật. Mỗi tài khoản giữ bản xem trước riêng; chỉ bấm Lưu mới đổi skin Microsoft/Ely.by và cape Microsoft đã sở hữu. Nếu một phần lưu lỗi, phần chưa lưu vẫn còn để thử lại.
- **Sửa mod dựa trên lỗi thực tế trong log:** chỉ đưa phương án sửa cho crash hoặc lỗi không tương thích có bằng chứng; metadata cảnh báo đơn thuần không còn biến thành lỗi bắt buộc sửa. Cuộn Nhật ký được chặn ở biên để tránh giật khi kéo quá tay.
- **Gọn và rõ hơn ở các thao tác nhỏ:** khôi phục icon nút, sửa chữ tràn ở Premium, canh giữa mũi tên tài khoản và làm nơi đăng xuất Google dễ tìm. Cosmetic dùng khối amethyst Minecraft; quyền host server được kiểm tra tự động khi cần.
- **Nhận kết quả rồi mới chạy bước tiếp theo:** trạng thái worker được hoàn tất trên luồng giao diện, giúp tránh bỏ mất kết quả tải phiên bản server hoặc checkout khi nhiều yêu cầu nối tiếp. Yêu cầu cũ hoàn tất không làm yêu cầu mới mất trạng thái bận.
- **Đăng nhập không bỏ lỡ lần đồng bộ đầu tiên:** nếu worker còn bận, yêu cầu đọc tài khoản được thực hiện ngay khi worker xong. Việc đăng xuất/hủy phiên hủy yêu cầu chờ, giữ cơ chế kiểm quyền từ server.
- **Giữ cách cập nhật quen thuộc:** launcher tự kiểm bản mới khi mở; người chơi bấm Cập nhật ngay để tải, kiểm SHA-256, cài và mở lại. Không tự tải hoặc khởi động lại khi chưa bấm cập nhật.
- **Gói phát hành dùng quyền thật:** không mở Ultimate TEST. Có Windows x64, Linux x64, macOS Intel và Apple Silicon; chỉ đính kèm bộ cài/gói portable, ZIP cập nhật và SHA256SUMS.

## Các cải tiến đã có trong rc13 — Từ log lỗi đến bản mod phù hợp

- **Sửa quầng blur ở cửa sổ thêm tài khoản:** popup không còn lấy chính mình làm nguồn mờ; hiệu ứng được giữ trong khung bo góc. Kiểm tra bằng renderer Qt thật, cả cửa sổ nhỏ và mức chữ 150%.
- **Kiểm tra mod đọc thêm log game:** đối chiếu `latest.log`, `debug.log` và báo cáo crash gần nhất với bộ mod, phiên bản Minecraft đang dùng. Nhận diện các mẫu thiếu/sai phiên bản phụ thuộc của Fabric, Forge và NeoForge; Free vẫn xem được lỗi.
- **Mỗi phương án có ô riêng:** icon mod, nền mica từ icon, phiên bản hiện tại → phiên bản đề xuất, Minecraft, loader và lý do từ log. Nhấn **Replace** ngay dưới ô để thay riêng mod đó cùng các phụ thuộc đã xác minh.
- **Chọn bản phù hợp thay vì chỉ chọn bản mới nhất:** dịch vụ xác minh nguồn bằng hash Modrinth, đối chiếu Minecraft, loader và yêu cầu từ những mod đang cài. File riêng hoặc lỗi runtime/mixin chưa đủ bằng chứng vẫn được báo để xử lý, không tự đoán bản thay thế.
- **Kiểm tra lại trước khi ghi:** đề xuất hoặc log thay đổi sẽ dừng thao tác; tải xong kiểm SHA-512 và quét lại phụ thuộc. Giữ bản trước sửa để hoàn tác, giữ nguyên worlds và những lỗi không liên quan khi thay riêng một mod; không ghi đè các bản mod đã tắt từ lần sửa trước.
- Log đầy đủ ở trên máy người chơi; dịch vụ chỉ nhận metadata và bằng chứng phụ thuộc đã tách cấu trúc, không nhận nguyên log, token hay đường dẫn cá nhân.

## Mới trong rc12 — Gọn hơn, liền mạch hơn

- **Sao lưu và nhập bản chơi đã có cửa sổ riêng đúng kích thước.** Sửa lỗi chữ và nút chồng lên trang Bản chơi; danh sách cuộn độc lập, vùng khôi phục luôn nằm trong cửa sổ. Kiểm tra ở 1024×600 và mức phóng chữ 150%.
- **Mica đồng nhất trên popup của launcher:** quản lý bản chơi/server, hồ sơ, bộ lọc, sửa mods, xác nhận thao tác, sao lưu, nhập và cập nhật. Render phần mềm có nền dễ đọc; bộ chọn file của hệ điều hành giữ giao diện hệ thống.
- **Cập nhật được trình bày rõ hơn:** thông báo kính gọn ở màn hình chính, changelog cuộn riêng, tiến độ tải và nút hành động cố định. Đóng thông báo theo phiên bản, không tự bật cửa sổ gây gián đoạn.
- **Nâng cấp chỉ trả phần còn lại:** backend khấu trừ phần tiền đã mua chưa sử dụng. Khi vừa mua, Plus → Pro 40.000đ, Pro → Max 40.000đ, Max → Ultimate 100.000đ; giá thực tế được tính theo thời hạn còn lại và xác nhận trước khi tạo đơn. Giá đơn đã tạo không trôi theo thời gian.
- **Giveaway từ web quản trị riêng:** chủ quản trị tìm người nhận bằng email Google, xác nhận tặng gói và xem lịch sử. Quà không tạo doanh thu giả hay tiền khấu trừ; thu hồi không ghi đè gói mua sau đó.
- **Website Nostalgia được làm mới:** bố cục thoáng, ảnh giao diện thật, bảng quyền lợi, FAQ và bộ chọn Windows/Linux/Mac Intel/Apple Silicon. Giữ màu Nostalgia và đường tải dự phòng khi API GitHub không phản hồi.
- Mục **Premium** với chú thích “Mua gói & nâng cấp” thay cho “Ủng hộ dự án”, giúp tìm nơi mua và nâng cấp gói nhanh hơn.
- Cắt gọn nhãn nút và placeholder dài, tránh chữ tràn qua ô kế bên.
- Khôi phục đủ định dạng phát hành: bộ cài, ZIP tự cập nhật, Linux portable và SHA256SUMS. Không đính kèm ảnh preview hay dữ liệu quản trị.

## Một giao diện có sức sống

- Giao diện mới dùng mặc định: bố cục gọn hơn, font Inter và Manrope hỗ trợ tiếng Việt, cùng màu nhấn quen thuộc.
- Home có key art Minecraft; khung tạo bản chơi lấy ảnh key art làm nền kính mờ và sắp xếp lựa chọn phiên bản/loader rõ ràng hơn.
- Chất liệu mica trong thư viện mods, modpacks, resourcepacks, shaders và các popup. Icon dự án hiện phía trước, ảnh mờ nằm phía sau thẻ.
- Danh sách phiên bản được thu gọn, có cuộn và xử lý trường hợp bị trôi khỏi lựa chọn mới nhất.
- Cuộn có quán tính và độ hãm; chuyển trang, mở popup, nút bấm, yêu thích và thanh điều hướng có chuyển động liền mạch hơn. Có tùy chọn giảm chuyển động.
- Icon khối ở thanh bên dùng model và texture Minecraft gốc, với hiệu ứng xoay khi tương tác.

## Thư viện và bản chơi, dễ quản lý hơn

- Nhấn vào ô nội dung để xem About, chọn bản phát hành và phiên bản Minecraft trước khi cài.
- Quản lý bản chơi có tổng quan, nội dung đã cài, hiệu năng, sao lưu và dữ liệu; các thao tác được đưa về cùng ngôn ngữ giao diện.
- Tự nhận diện metadata mods từ JAR trong modpack, hoạt động offline và dùng cache. Đối chiếu hash với nguồn công khai để bổ sung thông tin khi có thể; không đoán mod từ tên file.
- Giữ các bản vá Forge/NeoForge, bao gồm modpack dùng số Forge ngắn như `47.4.23`.

## Chơi cùng nhau, mang theo bộ mod của nhóm

- Google giữ tài khoản dịch vụ, Plus, bạn bè và hồ sơ khi đổi máy. Tài khoản Minecraft vẫn dùng cho việc vào game; hỗ trợ Microsoft, Ely.by và offline.
- Danh sách bạn bè có avatar, chat và lời mời chơi chung. Nhấn avatar cá nhân để mở hồ sơ.
- Host chọn bản chơi và mods chia sẻ trước khi khởi chạy Minecraft. Bộ pack được chụp lại trước lúc game chạy, giúp tránh thay đổi file giữa lúc truyền.
- **Một host có Plus, các bạn được mời nhận bộ pack miễn phí.** Với pack có nguồn xác minh được, launcher cài bản gốc và áp dụng phần thêm, sửa hoặc bỏ; pack tự xây dựng và file riêng được nhận từ host.
- **Khách cũng được chọn nội dung:** các tab Mods, Texture pack và Shader pack, tìm kiếm, chọn tất cả/bỏ chọn, icon và nền mica. File không có logo phù hợp dùng icon Minecraft thay thế.
- Trước khi nhận, khách phải xác nhận cảnh báo bảo mật. Mods và scripts có thể chạy mã; kiểm hash xác nhận toàn vẹn, không chứng minh file an toàn. Bỏ mod bắt buộc có thể khiến game không vào được phòng.
- **Đồng bộ lần sau là cập nhật:** xác định bằng tài khoản host đã xác thực và mã riêng của pack, không dựa vào tên hay mã phòng. Pack mới cùng tên không ghi đè bản cũ.
- Chỉ tải và ghi file thay đổi; giữ worlds và mods khách tự thêm. File trùng với nội dung riêng của khách bị chặn, phần cũ có sao lưu và lỗi ghi được phục hồi. Nội dung mới ở lần cập nhật mặc định chưa chọn.
- Texture pack nằm trong `resourcepacks`; người chơi chọn bật trong Minecraft, giữ tùy chọn cá nhân trên máy khách.

## Skin, cosmetic và hồ sơ

- Xem skin 3D với Steve/Alex, các lớp ngoài và thao tác xoay; giữ luồng thay skin Microsoft và Ely.by.
- Thư viện cosmetic riêng, với các bộ Amethyst, Grove và Eclipse; Plus chọn một trong ba bộ.
- Avatar, badge, decor, skin và modpack yêu thích tạo thêm nét riêng cho hồ sơ. Các quyền cosmetic trả phí được kiểm tra từ dịch vụ.
- Danh mục cosmetic có cấu trúc để thêm, ngừng phát hành hoặc vô hiệu hóa nội dung trong các lần cập nhật.

## Plus và công cụ cho nhóm chơi

| Gói | Thời hạn | Giá |
| --- | --- | ---: |
| Plus | 1 tháng | 29.000đ |
| Pro | 6 tháng | 69.000đ |
| Max | 1 năm | 109.000đ |
| Ultimate | Mua một lần | 209.000đ |

- Free báo các xung đột mod mà hệ thống nhận diện được; Plus có phương án sửa trong phạm vi hỗ trợ, kiểm file, sao lưu và hoàn tác.
- Pro, Max và Ultimate có công cụ tạo server **chạy trên máy host**: Paper, Purpur, Folia, Fabric và các biến thể Arclight được hỗ trợ. Cấu hình bằng UI, console, tìm/cài plugin hoặc mod, và xóa server.
- Thanh toán hiện dùng chuyển khoản Vietcombank với QR, mã đơn và duyệt giao dịch. Nút “Tôi đã chuyển khoản” gửi yêu cầu kiểm tra; Plus chỉ được cấp sau khi giao dịch được duyệt. Chưa dùng payOS để tự động xác nhận.
- Backend kiểm quyền đồng bộ và quyền trả phí; đổi máy hoặc thu hồi tài khoản sẽ làm mất quyền dịch vụ của phiên cũ. File đã tải về vẫn thuộc quyền kiểm soát của người chơi trên máy họ.

## Trước khi thử

- Cả host và khách nên dùng **rc13 trở lên** để có lựa chọn nội dung và cập nhật theo định danh pack. Bản đồng bộ từ client cũ thiếu định danh sẽ tạo một instance mới ở lần nhận đầu tiên; launcher không tự ghép theo tên để tránh ghi đè nhầm.
- Host cần giữ launcher và phòng đang hoạt động trong khi khách nhận file riêng. Không đồng bộ khi Minecraft trên máy khách đang chạy.
- Bản miễn phí vẫn chơi thường và nhận đồng bộ khi được host Plus mời. Các bộ cài trong bản phát hành giữ cơ chế kiểm quyền thật.
- Đã kiểm tra luồng chọn nội dung, cập nhật, chống ghi đè nhầm, kiểm hash, sao lưu/phục hồi và UI ở cửa sổ nhỏ/chữ 150%. Kiểm tra tự động không thay thế lượt thử chơi Minecraft thực tế trên hai máy.

**Tải đúng bộ cài cho hệ điều hành của bạn bên dưới.** Linux Mint/Ubuntu dùng `.deb`; Windows dùng `setup.exe`; macOS chọn `.dmg` arm64 hoặc x64. Gói ZIP và `SHA256SUMS` phục vụ tự cập nhật; Linux có thêm TAR.GZ để chạy portable. Không kèm ảnh preview hay tài liệu phụ.
