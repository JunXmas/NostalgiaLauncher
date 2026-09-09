import QtQuick

/* Dải tab kiểu web: chữ + gạch chân xanh trượt theo tab đang chọn. `tabs` là mảng chuỗi. */
Item {
    id: root
    property var tabs: []
    property int currentIndex: 0
    height: 36

    Row {
        id: row
        spacing: 22
        Repeater {
            model: root.tabs
            Item {
                id: tab
                width: caption.width
                height: root.height
                Text {
                    id: caption
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData
                    color: index === root.currentIndex ? Theme.text : Theme.textMuted
                    font.pixelSize: 13; font.bold: index === root.currentIndex; font.letterSpacing: 0.6
                    Behavior on color { ColorAnimation { duration: Theme.quick } }
                }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.currentIndex = index }
            }
        }
    }
    Rectangle {
        readonly property Item active: row.children[root.currentIndex] || null
        x: active ? active.x : 0
        width: active ? active.width : 0
        anchors.bottom: parent.bottom
        height: 2; radius: 1
        color: Theme.accent
        Behavior on x { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border; z: -1 }
}
