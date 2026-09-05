import QtQuick

/* Nút chơi. Nhấn xuống thì lún nhẹ — phản hồi tức thì quan trọng hơn mọi hiệu ứng khác. */
Item {
    id: root
    property string instanceLabel: ""
    property bool playable: true
    signal clicked()

    implicitWidth: 300
    implicitHeight: 76

    Rectangle {
        id: body
        anchors.fill: parent
        radius: Theme.radius
        color: root.playable ? (press.pressed ? Theme.accentDeep : Theme.accent) : Theme.surfaceHigh
        scale: press.pressed ? 0.98 : (hover.hovered && root.playable ? 1.02 : 1.0)

        Behavior on color { ColorAnimation { duration: Theme.quick } }
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        Column {
            anchors.centerIn: parent
            spacing: 3
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "CHƠI  ▶"
                color: root.playable ? "#06210f" : Theme.textMuted
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 2
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.instanceLabel
                color: root.playable ? "#0d3b1e" : Theme.textMuted
                font.pixelSize: 11
            }
        }
    }

    HoverHandler { id: hover; enabled: root.playable }
    TapHandler { id: press; enabled: root.playable; onTapped: root.clicked() }
}
