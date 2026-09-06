import QtQuick

/* Viên trạng thái nhỏ ở hàng đầu trang chủ: một ký hiệu hoặc một chấm màu, rồi chữ. */
Rectangle {
    id: root
    property string text: ""
    property string glyph: ""
    property color dotColor: "transparent"
    property bool pulsing: false

    width: content.width + 28
    height: 40
    radius: Theme.radiusSmall
    color: Theme.surface
    border.color: Theme.border
    border.width: 1

    Row {
        id: content
        anchors.centerIn: parent
        spacing: 8
        Text {
            visible: root.glyph.length > 0
            anchors.verticalCenter: parent.verticalCenter
            text: root.glyph; color: Theme.accent; font.pixelSize: 13
        }
        Rectangle {
            visible: root.glyph.length === 0
            anchors.verticalCenter: parent.verticalCenter
            width: 8; height: 8; radius: 4
            color: root.dotColor
            SequentialAnimation on opacity {
                running: root.pulsing
                loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 900 }
                NumberAnimation { to: 1.0; duration: 900 }
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text; color: Theme.text; font.pixelSize: 12
        }
    }
}
