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
    signal clicked()

    implicitHeight: 46
    width: parent ? parent.width : 0

    Rectangle {
        id: pill
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: root.selected ? Theme.surfaceHigh : (hover.hovered ? Theme.surface : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.quick } }

        // Vạch sáng bên trái: chỉ hiện ở mục đang chọn, và trượt vào chứ không nhảy.
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: 0
            width: 3
            height: root.selected ? parent.height * 0.55 : 0
            radius: 0
            color: Theme.accent
            Behavior on height { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        }
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 18
        spacing: 14

        BlockIcon {
            objectName: "navIcon"
            anchors.verticalCenter: parent.verticalCenter
            width: 22; height: 22
            block: root.block
            glyph: root.glyph
            glyphColor: root.selected ? Theme.accent : Theme.textMuted
            // Xoay khi rê vào mục, và xoay luôn ở mục đang chọn thì thanh bên không bao giờ
            // đứng yên — đốt CPU mà chẳng ai nhìn. Chỉ xoay lúc có chuột.
            spinning: hover.hovered
        }
        Text {
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
