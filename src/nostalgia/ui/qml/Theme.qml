pragma Singleton
import QtQuick

/*
  Bảng màu và nhịp chuyển động, gom một chỗ.

  Rải mã màu khắp các file QML là cách chắc chắn để một ngày có ba sắc xanh khác nhau cho
  cùng một ý nghĩa — đúng loại trôi dạt mà GLOSSARY.md chặn cho tên biến, nay chặn cho màu.
*/
QtObject {
    readonly property color background:  "#0a0d0b"
    readonly property color surface:     "#111713"
    readonly property color surfaceHigh: "#18201a"
    readonly property color border:      "#222c26"

    readonly property color accent:      "#4ade80"
    readonly property color accentDeep:  "#22a24f"
    readonly property color accentSoft:  "#1b3524"

    readonly property color text:        "#e9f1ec"
    readonly property color textMuted:   "#7f9488"
    readonly property color danger:      "#f2555a"
    readonly property color warning:     "#f5c451"

    /* Khối kiểu Bedrock (ActionButton, Toggle, Slider): viền tối, mặt sáng, cạnh dưới dày.
       Gom ở đây để nút, công tắc và thanh trượt không trôi thành ba sắc xám khác nhau. */
    readonly property color blockBorder:  "#1e1e1f"
    readonly property color blockFace:    "#48494a"
    readonly property color blockEdge:    "#2b2c2d"
    readonly property color blockOnFace:  "#3c8527"
    readonly property color blockOnEdge:  "#1d4d13"
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
