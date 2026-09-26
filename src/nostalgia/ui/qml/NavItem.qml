import QtQuick
import QtQuick.Controls

/* Một mục trong thanh bên. Hoạt ảnh nằm ở `Behavior`, không rải khắp nơi. */
Item {
    id: root
    property string label: ""
    property string glyph: ""
    // Tên khối Minecraft làm icon. Rỗng, hoặc chưa sinh xong dải, thì rơi về `glyph`.
    property string block: ""
    property bool selected: false
    /* Màu RIÊNG của mục này, không phải `Theme.accent`.

       Khác biệt quan trọng: `Theme.accent` là màu của tab ĐANG MỞ, nên nếu thanh bên dùng nó
       thì cả bảy mục cùng một màu và không còn nhận ra mục nào là mục nào. Mỗi mục giữ màu
       của chính nó, kể cả lúc không được chọn — đó là thứ làm thanh bên đọc được bằng màu. */
    property color tint: Theme.accent
    // Thu gọn: chỉ icon, không chữ — thanh bên hẹp thành cột khối.
    property bool compact: false
    signal clicked()

    implicitHeight: 46
    width: parent ? parent.width : 0

    Rectangle {
        id: pill
        anchors.fill: parent
        radius: Theme.radiusSmall
        // Mục đang chọn nhuộm nền theo màu của chính nó — nền xám trung tính như trước thì
        // bảy mục chọn nhìn giống hệt nhau.
        color: root.selected ? Theme.mix(Theme.surfaceHigh, root.tint, 0.22)
                             : (hover.hovered ? Theme.mix(Theme.surface, root.tint, 0.10)
                                              : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.quick } }

        // Vạch sáng bên trái: chỉ hiện ở mục đang chọn, và trượt vào chứ không nhảy.
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: 0
            // Dày 4 px chứ không 3: vạch mảnh là ngôn ngữ giao diện công cụ, còn nét dày,
            // đặc, không bo là ngôn ngữ hoạt hình — và nay nó còn phải tải được màu.
            width: 4
            height: root.selected ? parent.height * 0.62 : 0
            radius: 0
            color: root.tint
            Behavior on height { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        }
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        // Thu gọn thì icon đứng giữa cột; 22 là bề rộng của BlockIcon.
        anchors.leftMargin: root.compact ? Math.round((root.width - 22) / 2) : 18
        spacing: 14

        BlockIcon {
            objectName: "navIcon"
            anchors.verticalCenter: parent.verticalCenter
            width: 22; height: 22
            block: root.block
            glyph: root.glyph
            glyphColor: root.selected ? root.tint : Theme.textMuted
            // Xoay khi rê vào mục, và xoay luôn ở mục đang chọn thì thanh bên không bao giờ
            // đứng yên — đốt CPU mà chẳng ai nhìn. Chỉ xoay lúc có chuột.
            spinning: hover.hovered
        }
        Text {
            visible: !root.compact
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            // Tên mục là nhãn hoa ngắn: dùng font pixel. F2D không có kiểu đậm nên mục đang
            // chọn phân biệt bằng MÀU và vạch xanh bên trái, không bằng nét dày.
            font.family: Theme.pixel
            font.pixelSize: Theme.fontHeading
            font.letterSpacing: Theme.trackLabel
            color: root.selected ? Theme.text : Theme.textMuted
            Behavior on color { ColorAnimation { duration: Theme.quick } }
        }
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: root.clicked() }
}
