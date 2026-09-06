import QtQuick

/* Hộp chọn một mục: bấm mở danh sách ngay dưới, chọn xong tự đóng. `model` là mảng chuỗi. */
Item {
    id: root
    property var model: []
    property int currentIndex: -1
    property string placeholder: "Chọn..."
    readonly property string currentText: currentIndex >= 0 && currentIndex < model.length
                                          ? model[currentIndex] : ""
    property bool open: false
    // Mở lên trên khi hộp nằm sát mép dưới của một vùng có clip (vd dưới nút CHƠI trên hero).
    property bool dropUp: false
    signal activated(int index)

    height: 34
    z: open ? 50 : 0

    Rectangle {
        id: head
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: hover.hovered || root.open ? Theme.surfaceHigh : Theme.surface
        border.color: root.open ? Theme.accent : Theme.border
        border.width: 1
        Behavior on color { ColorAnimation { duration: Theme.quick } }

        Text {
            anchors { left: parent.left; leftMargin: 11; right: arrow.left; verticalCenter: parent.verticalCenter }
            text: root.currentText || root.placeholder
            color: root.currentText ? Theme.text : Theme.textMuted
            font.pixelSize: 12; elide: Text.ElideRight
        }
        Text {
            id: arrow
            anchors { right: parent.right; rightMargin: 11; verticalCenter: parent.verticalCenter }
            text: "⌄"; color: Theme.textMuted; font.pixelSize: 14
            rotation: (root.open !== root.dropUp) ? 180 : 0
            Behavior on rotation { NumberAnimation { duration: Theme.quick } }
        }
        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: root.open = !root.open }
    }

    Rectangle {
        id: popup
        objectName: "dropdownPopup"
        width: parent.width
        y: root.dropUp ? -height - 4 : head.height + 4
        height: root.open ? Math.min(root.model.length, 8) * 32 + 8 : 0
        visible: height > 0
        clip: true
        radius: Theme.radiusSmall
        color: Theme.surfaceHigh
        border.color: Theme.border
        border.width: 1
        Behavior on height { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        ListView {
            anchors { fill: parent; margins: 4 }
            model: root.model
            clip: true
            delegate: Rectangle {
                width: ListView.view.width
                height: 32
                radius: 6
                color: rowHover.hovered ? Theme.accentSoft : "transparent"
                Text {
                    anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                    text: modelData
                    color: index === root.currentIndex ? Theme.accent : Theme.text
                    font.pixelSize: 12
                }
                HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: { root.currentIndex = index; root.open = false; root.activated(index); }
                }
            }
        }
    }
}
