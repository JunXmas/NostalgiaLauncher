import QtQuick
import QtQuick.Controls

/* Một mục trong thanh bên. Hoạt ảnh nằm ở `Behavior`, không rải khắp nơi. */
Item {
    id: root
    property string label: ""
    property string glyph: ""
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
            radius: 2
            color: Theme.accent
            Behavior on height { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        }
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 18
        spacing: 14

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.glyph
            font.pixelSize: 17
            color: root.selected ? Theme.accent : Theme.textMuted
            Behavior on color { ColorAnimation { duration: Theme.quick } }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            font.pixelSize: 13
            font.letterSpacing: 1.1
            font.bold: root.selected
            color: root.selected ? Theme.text : Theme.textMuted
            Behavior on color { ColorAnimation { duration: Theme.quick } }
        }
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: root.clicked() }
}
