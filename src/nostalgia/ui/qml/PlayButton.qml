import QtQuick

/* Nút chơi lớn, kèm dải chọn bản chơi bên dưới — đúng bố cục bản mẫu. */
Column {
    id: root
    property string instanceLabel: ""
    property string versionId: ""
    property bool playable: true
    signal clicked()
    signal pickRequested()

    spacing: 0
    width: 300

    Rectangle {
        width: parent.width
        height: 64
        radius: Theme.radiusSmall
        color: root.playable ? (press.pressed ? Theme.accentDeep : Theme.accent) : Theme.surfaceHigh
        scale: press.pressed ? 0.985 : (hover.hovered && root.playable ? 1.015 : 1.0)
        Behavior on color { ColorAnimation { duration: Theme.quick } }
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        Text {
            anchors.centerIn: parent
            text: "CHƠI  ▶"
            color: root.playable ? "#06210f" : Theme.textMuted
            font.pixelSize: 24; font.bold: true; font.letterSpacing: 2
        }

        HoverHandler { id: hover; enabled: root.playable; cursorShape: Qt.PointingHandCursor }
        TapHandler { id: press; enabled: root.playable; onTapped: root.clicked() }
    }

    // Dải chọn bản chơi: cùng bề ngang, dính liền dưới nút.
    Rectangle {
        width: parent.width
        height: 40
        radius: Theme.radiusSmall
        color: pickHover.hovered ? Theme.surfaceHigh : "#d9111713"
        border.color: Theme.border
        border.width: 1
        Behavior on color { ColorAnimation { duration: Theme.quick } }

        Row {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            spacing: 9
            Rectangle {
                width: 18; height: 18; radius: 4; color: Theme.accentDeep
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.instanceLabel + (root.versionId ? "  (" + root.versionId + ")" : "")
                color: Theme.text; font.pixelSize: 12
            }
        }
        Text {
            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
            text: "⌄"; color: Theme.textMuted; font.pixelSize: 14
        }

        HoverHandler { id: pickHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: root.pickRequested() }
    }
}
