Bản vá cho 1.1.1 — dọn phần lọc trong THƯ VIỆN, từ một phản hồi của người chơi: "cài
modpack không thấy được hết mọi thứ, mà phần lọc phiên bản thì vướng". Hoá ra đó là ba lỗi
riêng biệt nằm cạnh nhau.

## Tìm modpack không còn bị ghim vào phiên bản của bản chơi đang chọn

Chọn bản chơi xong thì bộ lọc tự nhảy về loader + phiên bản của bản chơi đó. Hợp lý cho mod
và shader — chúng cài **vào** bản chơi. Nhưng **sai hoàn toàn với modpack**: modpack *tạo ra*
một bản chơi mới. Hậu quả: bản chơi đang chọn là 1.21 thì mọi pack 1.7.10 bị giấu, và kho
trông như chỉ có vài chục pack thay vì hơn mười tám nghìn.

Nay bấm chip **Modpack** là thả hết bộ lọc thừa hưởng. Bộ lọc bạn **tự** tick vẫn giữ nguyên
khi đổi chip — chỉ bộ lọc mặc định mới bị đặt lại.

## Danh mục phiên bản không còn bị cắt còn 60 mục

Cột lọc cũ cắt danh mục Mojang (hơn 500 bản) xuống 60 mục cho vừa bề ngang cột, và không nói
một chữ nào về việc đã cắt. Ai tìm bản cũ thì cuộn mãi không ra. Khay mới cuộn được nên giữ
nguyên cả danh mục, kèm ô tìm riêng bên trong.

## Cột lọc dọc thành ba ô ngang thu gọn

Cột trái 210px trải thẳng 4 loader cộng hàng chục phiên bản theo chiều dọc, đẩy phần **Sắp
xếp** ra khỏi tầm mắt. Nay là ba ô cùng một dòng — **Mọi loader** / **Mọi phiên bản** /
**Liên quan** — bấm mới bung khay, bấm ra ngoài thì đóng.

- Ô đóng vẫn nói được đang lọc gì: một mục thì hiện tên nó, nhiều mục thì `1.21.4 +2`.
- Dấu **✕** ngay trên ô xoá cả nhóm, không phải bỏ tick từng mục.
- Bỏ cột nên phần kết quả rộng thêm 234px, và số cột thẻ tính theo bề ngang cửa sổ thật thay
  vì ghim cứng hai cột.

## Nút Ủng hộ dự án trong CÀI ĐẶT

Launcher miễn phí, không quảng cáo, không bản trả tiền. Nút nằm im ở hàng "Phiên bản
launcher" — không popup, không nhắc theo lịch, không chặn tính năng nào.

---

Cập nhật: launcher tự tải bản này (trừ bản macOS `.app` và bản chạy từ mã nguồn — hai loại đó
mở trang tải). Mọi gói đều phải khớp `SHA256SUMS` mới được cài.
