import QtQuick

/* Thẻ một bản chơi. Nhô lên khi rê chuột, và xuất hiện lệch nhau một nhịp cho đỡ khô. */
Rectangle {
    id: root
    property string label: ""
    property string versionId: ""
    property int index: 0

    width: 232
    height: 132
    radius: Theme.radius
    color: hover.hovered ? Theme.surfaceHigh : Theme.surface
    border.color: hover.hovered ? Theme.accent : Theme.border
    border.width: 1
    y: 0
    opacity: 0

    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }

    // Xuất hiện: trượt lên và mờ dần, mỗi thẻ chậm hơn thẻ trước 60ms.
    Component.onCompleted: appear.start()
    ParallelAnimation {
        id: appear
        NumberAnimation { target: root; property: "opacity"; from: 0; to: 1
                          duration: Theme.slow; easing.type: Easing.OutCubic }
        NumberAnimation { target: root; property: "y"; from: 14; to: 0
                          duration: Theme.slow; easing.type: Easing.OutCubic }
        PauseAnimation { duration: 0 }
    }

    Column {
        anchors { fill: parent; margins: 16 }
        spacing: 8

        Rectangle {
            width: 40; height: 40; radius: 8; color: Theme.accentDeep
            Text { anchors.centerIn: parent; text: "▣"; color: "white"; font.pixelSize: 20 }
        }
        Text {
            text: root.label
            color: Theme.text
            font.pixelSize: 15
            font.bold: true
            width: parent.width
            elide: Text.ElideRight
        }
        Text {
            text: root.versionId
            color: Theme.textMuted
            font.pixelSize: 11
        }
    }

    HoverHandler { id: hover }
}
