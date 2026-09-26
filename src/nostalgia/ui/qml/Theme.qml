pragma Singleton
import QtQuick

/*
  Bảng màu và nhịp chuyển động, gom một chỗ.

  Rải mã màu khắp các file QML là cách chắc chắn để một ngày có ba sắc xanh khác nhau cho
  cùng một ý nghĩa — đúng loại trôi dạt mà GLOSSARY.md chặn cho tên biến, nay chặn cho màu.
*/
QtObject {
    /* Nền xám lạnh, KHÔNG phải đen ngả lục như trước (`#0a0d0b`).

       Lý do đo được: bảng accent bên dưới nay có bảy sắc trải khắp vòng tròn màu. Nền ngả lục
       làm sắc tím và hồng trông bẩn — hai màu đối nghịch đặt cạnh nhau thì màu yếu hơn ngả
       xám. Nền trung tính về sắc độ là điều kiện để cả bảy sắc cùng đọc được. Nền cũng sáng
       hơn một bậc: đen tuyền đọc ra "cửa sổ dòng lệnh", còn giao diện game thì có màu. */
    readonly property color background:  "#141821"
    readonly property color surface:     "#1c212c"
    readonly property color surfaceHigh: "#262d3a"
    readonly property color border:      "#333c4d"

    /* Màu nhấn đổi theo tab đang mở — bảy mục, bảy sắc.

       Trước đây cả launcher dùng đúng một sắc lục cho 94 chỗ, nên bảy trang nhìn như một
       trang. Nay mỗi trang mang màu của chính khối icon nó (cỏ, bàn chế đồ, kệ sách, kim
       cương, khối lệnh, rương, đá đỏ) — chuyển tab là cả trang đổi sắc, và người dùng biết
       mình đang ở đâu mà không cần đọc chữ.

       `page` do Sidebar ghi vào. Đây là property DUY NHẤT ghi được trong file này; mọi thứ
       khác vẫn readonly để không ai lén đổi màu từ chỗ khác. */
    property int page: 0

    readonly property var accents: [
        "#5ac54f",  // TRANG CHỦ   — cỏ
        "#e8a33d",  // BẢN CHƠI    — gỗ bàn chế đồ
        "#b06ee6",  // THƯ VIỆN    — kệ sách
        "#3ecfd5",  // TÀI KHOẢN   — kim cương
        /* CHƠI CHUNG — hồng sen (320°), không phải `#f25f8a` (345°) thử lần đầu.

           Sắc kia đúng tông khối lệnh nhưng đo trên ảnh thì nó ngả đỏ: đứng cạnh `danger`
           (#f2555a, 358°) trong cùng khung hình là hai màu đọc ra cùng một nghĩa. Dịch lên
           320° đủ để mắt tách ra, và 320° cũng chính là khoảng trống cuối cùng còn lại của
           vòng màu — sáu sắc kia đã chiếm 100/40/274/182/220 và xám. */
        "#ef63b9",
        "#5b8dee",  // NHẬT KÝ     — rương
        // CÀI ĐẶT — SẮT, không phải đá đỏ như icon của nó.
        //
        // Đá đỏ là màu đúng về mặt khối, nhưng đo trên ảnh chụp thì nó trùng `danger` (#f2555a):
        // ở trang CÀI ĐẶT mọi công tắc ĐANG BẬT hoá đỏ, đọc ra "cảnh báo" đúng chỗ đáng ra
        // phải đọc là "xong". Một màu chỉ được mang một nghĩa — đỏ đã là nghĩa nguy hiểm.
        "#9fb0c9"
    ]

    readonly property color accent: accents[Math.max(0, Math.min(page, accents.length - 1))]
    // Sinh ra từ `accent` chứ không viết tay 14 mã màu: viết tay thì thêm một tab là thêm hai
    // chỗ để quên, và hai sắc đó chắc chắn sẽ lệch nhau theo thời gian.
    readonly property color accentDeep: Qt.darker(accent, 1.55)
    readonly property color accentSoft: mix(background, accent, 0.20)

    // Màu thương hiệu: chữ "GIA" ở logo. Đứng ngoài bảng `accents` vì nó KHÔNG được đổi theo
    // tab — tên sản phẩm phải nhận ra được ở cả bảy trang.
    readonly property color brand:       "#5ac54f"

    readonly property color text:        "#eef1f7"
    readonly property color textMuted:   "#8d97ab"
    readonly property color danger:      "#f2555a"
    readonly property color warning:     "#f5c451"

    /* Khối kiểu Bedrock (ActionButton, Toggle, Slider): viền tối, mặt sáng, cạnh dưới dày.
       Gom ở đây để nút, công tắc và thanh trượt không trôi thành ba sắc xám khác nhau. */
    readonly property color blockBorder:  "#1e1e1f"
    readonly property color blockFace:    "#48494a"
    readonly property color blockEdge:    "#2b2c2d"
    // Mặt nút "đang bật" phải là màu của tab, không phải sắc lục cố định `#3c8527`: nút chính
    // và tiêu đề trang nằm cùng một màn hình, lệch màu thì tab đổi sắc mà nút thì không.
    readonly property color blockOnFace:  accent
    readonly property color blockOnEdge:  Qt.darker(accent, 1.9)
    readonly property color blockLight:   "#d0d1d2"
    readonly property color blockTrack:   "#2b2c2d"
    readonly property color blockGlint:   "#33ffffff"

    /* Chữ.

       Hai họ font, mỗi họ một việc. `sans` cho mọi thứ đọc được; `pixel` CHỈ cho nhãn viết
       hoa ngắn — nó không có kiểu đậm nên đặt vào đoạn văn là mất luôn cấp bậc chữ, và dấu
       tiếng Việt chồng cao làm dòng chữ gồ ghề.

       Năm bậc, không hơn. Trước khi gom, 57 file QML rải tay 18 cỡ chữ khác nhau: mỗi trang
       viết ở một thời điểm nên nhặt một cỡ cho cùng một vai trò, và đó chính là thứ làm các
       tab nhìn không giống nhau. Cùng lý do bảng màu đã gom ở trên. */
    readonly property string sans:  "Inter"
    readonly property string pixel: "Minecraft F2D V1.42"
    readonly property string mono:  "monospace"

    readonly property int fontHero:    30   // câu chào trang chủ
    readonly property int fontTitle:   18   // tiêu đề hộp thoại
    readonly property int fontHeading: 13   // tên thẻ, tên mục
    readonly property int fontBody:    12   // chữ đọc chính
    readonly property int fontLabel:   10   // nhãn viết hoa, chú thích

    // Giãn chữ: chỉ hai giá trị. Giãn rộng làm chữ thường khó đọc — nó chỉ hợp nhãn hoa ngắn.
    readonly property real trackLabel: 1.2
    readonly property real trackBody:  0

    /* Góc vuông, không bo.

       Đo trên chính CSS của minecraft.net: `border-radius: 0` xuất hiện 57 lần, và không có
       một giá trị bo nào khác ngoài `50%` cho bốn hình tròn. Mọi thứ ở đó đều là khối vuông.
       Giữ hai tên cũ để 10 chỗ đang dùng không phải sửa một lượt, nhưng giá trị nay là 0. */
    readonly property int radius:        0
    readonly property int radiusSmall:   0
    readonly property int gap:           14
    readonly property int pad:           18

    // Một nhịp duy nhất cho mọi hoạt ảnh nhỏ. Mỗi chỗ một tốc độ khác nhau làm giao diện
    // trông rời rạc, dù từng chỗ nhìn riêng vẫn mượt.
    readonly property int quick:         120
    readonly property int normal:        220
    readonly property int slow:          420

    /* Pha `ratio` phần `b` vào `a`.

       Dùng thay cho việc viết tay một mã màu nền-nhạt cho mỗi sắc nhấn: bảy sắc thì sẽ là
       bảy mã viết tay, và chỉ cần một mã lệch tông là một tab nhìn khác hẳn sáu tab kia.
       Không dùng `Qt.tint` vì nó phủ bằng alpha — nền trong suốt chồng lên nhau sẽ ra màu
       khác nhau tuỳ thứ nằm dưới, đúng thứ cần tránh. */
    function mix(a, b, ratio) {
        return Qt.rgba(a.r + (b.r - a.r) * ratio,
                       a.g + (b.g - a.g) * ratio,
                       a.b + (b.b - a.b) * ratio, 1);
    }

    /* 1234567 -> "1,2M": số tải/theo dõi trên thẻ mod. */
    function compact(count) {
        if (count >= 1000000) return (count / 1000000).toFixed(1).replace(".", ",") + "M";
        if (count >= 1000) return (count / 1000).toFixed(1).replace(".", ",") + "K";
        return String(count);
    }

    /* 20971520 -> "20,0 MB": dung lượng file đã cài. */
    function fileSize(bytes) {
        if (bytes >= 1048576) return (bytes / 1048576).toFixed(1).replace(".", ",") + " MB";
        if (bytes >= 1024) return (bytes / 1024).toFixed(1).replace(".", ",") + " KB";
        return bytes + " B";
    }
}
