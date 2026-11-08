# Đề xuất nâng cấp Nostalgia+

Ngày: 07/11/2026. Trạng thái: đề xuất sản phẩm để review; chưa thay giá, quyền lợi,
checkout hoặc cấu hình production. Tạm dừng triển khai marketplace theo yêu cầu
để chốt hướng Plus trước.

Hướng mới đã thống nhất: bỏ cơ chế lật thẻ và chọn giá ngẫu nhiên. Quản trị đặt
giá coin cho từng item/combo; người chơi nạp coin để mua. Điểm thưởng theo ngày
chỉ dành cho Plus đang hiệu lực, gồm lifetime, và chỉ dùng giảm một phần giá mua.
Điểm thưởng và coin đã nạp là hai số dư độc lập. Các tham số thưởng chưa được
định giá; phải cấu hình rõ trước khi bật, không lấy ví dụ trong tài liệu làm giá thật.

Quyết định mới của chủ dự án: bỏ trading khỏi marketplace và quyền lợi Plus,
bao gồm gói năm và mua đứt. Cosmetic đã mua gắn tài khoản sở hữu; không có luồng
người chơi trao đổi, bán lại hoặc chuyển đồ giữa các tài khoản trong thiết kế này.

## 1. Giá trị muốn bán

Nostalgia+ nên đem lại một diện mạo riêng và sự tiện lợi dùng thường xuyên.
Người mua cần thấy được ngay thứ nhận được, dùng ở đâu và giữ được gì khi hết hạn.

Định vị đề xuất: “Bộ sưu tập riêng. Diện mạo của bạn. Tiện lợi trên mọi máy.”

Hiện tại `shared/catalog.js` của backend có ba nhóm quyền: trang trí hồ sơ, màu
hồ sơ và huy hiệu. Launcher giới thiệu thêm quyền dùng bản thử nghiệm sớm. Giá
đang cấu hình là 79.000đ/12 tháng và 199.000đ mua đứt trong thời gian dịch vụ hoạt
động. Đây là điểm xuất phát, không phải mức giá mới được phê duyệt.

Mình đánh giá các quyền hiện tại chưa đủ tạo lý do sử dụng thường xuyên. Quyền
preview là quyền phụ; không nên lấy việc thử bản có thể lỗi làm điểm bán chính.

## 2. Gói quyền lợi đề xuất

| Quyền lợi | Tài khoản thường | Nostalgia+ | Ưu tiên |
| --- | --- | --- | --- |
| Chơi game, mod/modpack, skin, lyrics, sky và tính năng hiện có | Giữ nguyên | Giữ nguyên | Bắt buộc |
| Mua món lẻ/combo bằng coin, giữ và đồng bộ đồ đã mua | Có | Có | Marketplace nền tảng |
| Người khác nhìn thấy cosmetic trong phạm vi Nos hỗ trợ | Có | Có | Marketplace nền tảng |
| Khung, nền, màu hồ sơ và huy hiệu Plus | Quyền hiện có/quà đã cấp | Bộ Plus, xem trước trực tiếp | Đợt đầu |
| Bộ trang trí chào mừng | Mua riêng nếu có bán | Nhận một lần theo tài khoản | Đợt đầu |
| Thư viện diện mạo Plus | Mặc thử, mua riêng món được bán | Dùng bộ sưu tập khi Plus còn hạn | Sau khi đồng bộ game ổn định |
| Điểm thưởng ngày | Không có quyền nhận điểm Plus | Nhận điểm để giảm một phần giá mua | Sau khi chính sách được cấu hình và kiểm thử |
| Lưu hồ sơ thiết lập cục bộ, xuất/nhập thủ công | Có | Có | Giữ miễn phí |
| Thư viện hồ sơ thiết lập trên cloud | Không thuộc gói thường | Lưu/chọn trên các máy, có lịch sử khôi phục giới hạn | Đợt tiếp theo |

“Bộ chào mừng” và “thư viện Plus” là hai loại quyền khác nhau. Không ghi chung là
“sở hữu” rồi thu lại món người chơi tưởng đã mua.

### Nhận được ngay

- Một bộ trang trí hồ sơ hoàn chỉnh gồm khung, nền và màu đồng bộ. Có artwork rõ,
  preview trên hồ sơ thật; không chỉ một nhãn Plus.
- Khi marketplace và quyền phân phối cosmetic đã sẵn sàng, bộ chào mừng có thể
  thêm hai món in-game phối được với nhau. Chỉ công bố khi asset đã có và đã test.
- Quà chào mừng đã nhận được giữ khi Plus hết hạn; không cấp lại khi gia hạn,
  đổi gói, đăng nhập máy khác hoặc chuyển từ gói năm sang mua đứt.
- Quà gắn với tài khoản nhận, không chuyển sang tài khoản khác.

### Có lý do dùng tiếp

- Thư viện Plus ban đầu gồm khoảng 3–5 bộ có chất lượng, phối đồng bộ với theme
  launcher; ưu tiên ít nhưng hoàn chỉnh. Đây là mục tiêu sản xuất, chưa có đủ asset.
- Công bố danh sách bộ đang có. Chỉ hứa nhịp bổ sung mới khi đã có người làm và
  lượng artwork dự phòng; chưa quảng cáo “mỗi tháng một bộ mới” lúc này.
- Khi hết hạn, quyền dùng bộ Plus tạm dừng. Món đã mua riêng bằng coin và quà
  chào mừng vẫn giữ nguyên. Không xóa bản mua chỉ vì trùng mẫu trong thư viện Plus.
- Nếu người dùng mua riêng một món đang dùng qua Plus, giao diện ghi rõ đó là
  mua quyền giữ lâu dài. Không tính quyền mượn từ Plus thành quyền sở hữu vĩnh viễn.
- Trước khi một bộ rời thư viện, ghi lịch rõ; không tạo khan hiếm giả hoặc đếm
  ngược không có thời hạn thật. Đợt đầu nên giữ danh mục ổn định.

### Ưu đãi dễ hiểu

- Giá do quản trị đặt theo coin, không quay hoặc lật thẻ để quyết định giá.
- Điểm thưởng ngày của Plus chỉ giảm một phần giá cosmetic; còn lại thanh toán
  bằng coin trong ví. Điểm không dùng mua Plus hoặc nạp thêm coin.
- Combo có món đã sở hữu được tính phần thiếu trước. Điểm áp dụng lên khoản mua
  còn thiếu, không bù thành coin, không thu phí lần nữa cho món đã sở hữu.
- Backend chốt cả giá, điểm sẽ dùng và coin sẽ trừ; client không tự tính quyền
  giảm giá. Điều kiện thay đổi sau quote phải xác nhận lại trước khi trừ số dư.
- Mức giảm mặc định 10% và các mức ưu đãi tuần trước đây chỉ là đề xuất cũ,
  chưa được phê duyệt; không tự cộng thêm hoặc chồng lên điểm thưởng ngày.

### Đồng bộ tiện ích có giới hạn

- Đồng bộ các hồ sơ thiết lập launcher được người dùng chủ động lưu, bộ sưu tập
  dự án yêu thích và theme đã chọn. Đề xuất beta: 10 hồ sơ, tối đa 50 KB/hồ sơ.
- Không tính việc đồng bộ ví, inventory hay đồ đã mua thành quyền Plus: những
  chức năng đó cần hoạt động cho mọi người mua cosmetic.
- Có revision và bản xem khác biệt khi hai máy sửa cùng lúc; không âm thầm ghi
  đè cấu hình đang dùng. Khôi phục là thao tác người dùng xác nhận.
- Không đồng bộ world, toàn bộ modpack, log, token hoặc đường dẫn máy cá nhân
  trong bản đầu. Tránh nhận một nghĩa vụ lưu trữ lớn chỉ để làm danh sách quyền lợi dài.
- Chỉ kiểm bản sửa mới khi mở tính năng/đăng nhập hoặc người dùng lưu; không
  heartbeat ghi dữ liệu định kỳ. Lưu dữ liệu dịch vụ này tách khỏi thống kê tùy chọn.
- Khi Plus hết hạn, giữ bản cục bộ và cho xuất dữ liệu cloud trong thời hạn đã
  công bố. Đề xuất 30 ngày để lấy bản sao trước khi xóa dữ liệu cloud; cần chốt
  chính sách trước khi bật, không ghi như hành vi đã có.

## 3. Giá và người đã mua

- Giữ 79.000đ/năm ở đợt nâng cấp đầu để đo giá trị sản phẩm, chưa tăng giá chỉ
  vì thêm danh sách quyền lợi. Hiện trả trước 12 tháng, không tự gia hạn.
- Giữ nguyên quyền của người đã mua gói năm/mua đứt và các gói cũ còn hiệu lực.
  Người mua đứt hiện tại được hưởng quyền Plus được nâng cấp, không bắt mua lại.
- Không cộng coin định kỳ vào gói mua đứt: 199.000đ chỉ tương đương khoảng 2,52
  lần phí năm hiện tại, trong khi quyền cấp coin vô hạn có thể kéo dài nhiều năm.
- Sau khi biết chi phí và nhu cầu, đề xuất cân nhắc ngừng bán mua đứt cho đơn
  mới nếu Plus bao gồm dịch vụ vận hành thường xuyên. Không thay đổi đơn đã mua.
  Đây là quyết định kinh doanh còn cần chủ dự án chốt, không phải thay đổi đã áp dụng.
- Có thể thử gói 3 tháng 29.000đ sau khi đối soát ổn định; giá này là đề xuất thử,
  chưa được đưa vào checkout. Chưa thêm gói tháng khi còn duyệt chuyển khoản thủ công.
- Phân biệt ủng hộ tùy tâm, mua Plus và nạp coin. Màn thanh toán cho biết rõ đơn
  đang mua loại nào; bấm “đã chuyển khoản” không được tự cộng quyền hoặc coin.

## 4. Trang giới thiệu trong launcher

Phần trên cùng hiển thị hồ sơ và nhân vật đang chọn, có chuyển trước/sau Plus.
Ba nội dung nổi bật: bộ chào mừng thực tế, bộ sưu tập Plus đang dùng được, tiện ích
đồng bộ đã hoạt động. Một mục chỉ được xuất hiện như quyền đã có sau khi triển khai.

Bên dưới là so sánh ngắn tài khoản thường/Plus, giá trả trước, thời hạn và nút mua.
Mỗi quyền có ví dụ nhìn được hoặc nút thử, thay cho các dòng mô tả chung chung.

Trên trang sản phẩm marketplace, hiển thị giá thường, giá Plus và điều kiện nếu có;
không bật popup ép mua Plus trước khi cho mua món lẻ. Trong Tủ đồ, tách nhãn:
“Đã mua”, “Quà được giữ” và “Dùng qua Plus”. Trang tài khoản cho biết rõ ngày hết
hạn và điều gì còn giữ sau đó.

Người mua được biết rõ các giới hạn tương thích: ảnh hồ sơ hiển thị trong launcher;
cosmetic in-game đầu tiên cần Nos Client và phiên bản/phòng được hỗ trợ. Không
quảng cáo mọi server, mọi client, Horizon hoặc mọi bản Minecraft đều nhìn thấy.

## 5. Thứ tự triển khai và điều kiện bàn giao

1. Hoàn thiện marketplace nền tảng: mua món lẻ/combo, đối soát coin, chứng minh
   ownership, chữ ký diện mạo, cache, đồng bộ hai Nos. Test rollback/retry trước.
2. Làm lớp quyền Plus rõ ràng: quyền theo membership và quyền sở hữu vĩnh viễn
   tách riêng; giữ gói cũ. Thêm quote ưu đãi và cấp quà một lần có chống trùng.
3. Làm trang Plus mới với asset thật và bộ chào mừng; kiểm tiếng Việt/Anh, cửa sổ
   nhỏ, chữ lớn, preview, hết hạn và các dòng mô tả không hứa quá phạm vi.
4. Mở thư viện Plus khi đủ asset và đồng bộ đã ổn; sau đó triển khai cloud preset
   với quota/revision/khôi phục và chính sách xóa dữ liệu đã công bố.

Các kiểm thử Plus cần bổ sung: nhận quà hai lần/đồng thời; gia hạn không cấp lại;
Plus hết hạn/thu hồi giữa quote và commit; giảm giá combo có item đã mua; mua
quyền vĩnh viễn của món đang mượn; chỉ quyền mượn bị tắt khi hết hạn; người mua
đứt cũ giữ quyền; mạng lỗi không mất item/số dư; xung đột và xuất dữ liệu cloud.

## 6. Đánh giá có thuyết phục hơn không

Theo dõi doanh thu đơn đã duyệt, số người mua Plus mới, số đơn gia hạn, nâng cấp,
hoàn tiền và chi phí phục vụ. Trình bày đây là dữ liệu giao dịch của khách hàng,
không phải số toàn bộ người chơi. Không suy từ lần đăng nhập thành đồng ý analytics.

Thu nhận phản hồi tự nguyện về lý do mua/không mua. Nếu đo trang đã xem hoặc hành vi
khác, phải nằm trong cơ chế đồng ý riêng và schema được công khai; kế hoạch này
không tự thêm luồng theo dõi hoặc đo retention xuyên ngày cho launcher.

Sau một chu kỳ sử dụng thực tế, đánh giá bộ nào hấp dẫn, quyền nào có nhu cầu,
chi phí cloud và công chăm sóc nội dung. Chưa đặt mục tiêu tỷ lệ chuyển đổi khi
chưa có mẫu đo và số liệu nền đáng tin.

## 7. Phạm vi thương mại và nguồn tham khảo

Phần cosmetic in-game trong đề xuất vẫn phụ thuộc việc làm rõ quyền cho
đúng mô hình mod/launcher đang xây; không suy ra đã được phép vì client khác có
bán. Không lấy cape làm quyền lợi bán mặc định. Hướng dẫn Minecraft có điều khoản
riêng về cape trên server và việc mod kiểm tra sản phẩm/dịch vụ ngoài game.

- [Minecraft Usage Guidelines](https://www.minecraft.net/en-us/usage-guidelines),
  mục Servers and hosting và Extended functionality and modifications.
- [Lunar+](https://store.lunarclient.com/category/plus) hiện kết hợp bộ cosmetic,
  ưu đãi cửa hàng và quyền cộng đồng. Dùng để tham khảo cách nhóm giá trị, không
  sao chép asset hoặc coi đó là bằng chứng cấp phép cho Nostalgia.
- [Laby+](https://laby.net/shop/plus) công bố thời hạn trả trước và không tự gia hạn.
  Đây là ví dụ về cách ghi điều kiện rõ ràng, không phải mức giá đề xuất cho Nostalgia.

Nguồn đối chiếu ngày 07/11/2026. Nhận định về sức hấp dẫn và ưu tiên ở trên là đề
xuất sản phẩm; chưa có thử nghiệm thị trường chứng minh kết quả bán hàng.

## 8. Cửa hàng giá coin và điểm thưởng ngày

Chủ dự án chọn mô hình sau trong phần thảo luận mới nhất:

- Không có lật thẻ hoặc ưu đãi được quyết định ngẫu nhiên trong luồng mua.
- Giá từng item/combo do quản trị đặt theo coin, được hiển thị trước khi mua.
- Người dùng nạp coin bằng gói có giá VND và số coin rõ, quản trị đối soát tiền.
- Chỉ Plus đang hiệu lực, gồm lifetime, được nhận điểm thưởng ngày.
- Điểm là ưu đãi giảm một phần giá mua; không cộng trực tiếp vào coin đã nạp.
- Không có trading/chuyển điểm hoặc coin giữa tài khoản.

### Cách nhận điểm

Đề xuất thao tác chủ động “Nhận điểm ngày” trong launcher sau khi đăng nhập
Google. Không cần chạy Minecraft, đo thời gian chơi hoặc đồng ý analytics.
Mỗi tài khoản nhận tối đa một lần trong một ngày UTC theo thời gian server,
reset 00:00 UTC, tức 07:00 tại Việt Nam. Launcher hiển thị giờ nhận tiếp theo.
Không cần client giữ kết nối hoặc gửi heartbeat để đủ điều kiện nhận.

Retry, mở nhiều máy hoặc nhấn cùng lúc vẫn chỉ nhận một lần. Backend dùng khóa
UNIQUE(account_id,day) và transaction, kiểm phiên/Plus tại lúc cấp. Ngày không
nhận không tự tạo điểm chờ hoặc cộng bù. Đây là đề xuất vận hành để triển khai,
chưa phải hành vi đã vận hành trên production.

### Quản trị cấu hình

Các thông số cần được thể hiện và xác nhận trước khi bật:

- Điểm nhận mỗi ngày, quy đổi điểm sang mức giảm bằng coin.
- Tỷ lệ tối đa của giá cosmetic được trả bằng điểm.
- Hạn sử dụng của điểm, nếu có, và cách xử lý điểm còn lại khi Plus hết hạn.
- Phạm vi sản phẩm áp dụng; giá gói nạp coin không được trả bằng điểm.

Chưa chọn con số cho các thông số này. Không tự bật mặc định hoặc áp dụng mức
60% của Silent Client. Nếu có hạn sử dụng, giao diện phải ghi rõ trước khi nhận;
không thay đổi ngược thời hạn của lô điểm đã cấp. Coin đã nạp không bị hết hạn
hoặc xóa theo chính sách điểm thưởng. Chính sách mới chỉ áp cho lần cấp sau theo
revision và thời điểm hiệu lực đã công bố.

Plus năm và lifetime dùng cùng quy tắc nhận điểm, chỉ khác thời hạn quyền Plus.
Không cần chuyển đổi/hủy lifetime để triển khai cơ chế này. Đồ đã mua vẫn giữ
độc lập với trạng thái thành viên. Bộ quà/lịch sự kiện khác phải được chốt riêng,
không tự biến thành nghĩa vụ tặng hàng tuần từ các đề xuất cũ.

### Khi mua

Checkout hiển thị giá coin từ server, số điểm định dùng, phần được giảm, số coin
còn phải trả và hai số dư sau mua. Người chơi chọn có dùng điểm hay không. Điểm
không làm chi phí mua âm và không tạo lại coin thừa. Nếu có nhiều lô điểm, ưu
 tiên dùng lô hết hạn sớm; không tiêu điểm đã hết hạn. Điểm và coin được trừ cùng
với cấp vật phẩm trong một transaction. Thất bại thì hoàn tác tất cả.

Retry sau khi mất phản hồi trả lại giao dịch đã thực hiện; không trừ điểm hoặc
coin lần nữa. Quyền và giá thay đổi sau quote yêu cầu chốt lại; không lặng lẽ
thu thêm. Trước khi bật cần kiểm đồng thời claim/mua, nhiều máy tranh số dư,
điểm hết hạn, giá/policy thay đổi, phiên/Plus bị thu hồi và lỗi giữa transaction.

### Minh bạch dữ liệu

Dữ liệu nhận/tiêu điểm phục vụ thực hiện quyền lợi và đối soát, tách khỏi thống
kê sử dụng tùy chọn. Không dùng chúng để lén ghi nhận thời gian chơi, địa chỉ
server, world, chat hoặc thông tin phần cứng. Tắt analytics không chặn mua hàng
hoặc nhận điểm theo chính sách này.
