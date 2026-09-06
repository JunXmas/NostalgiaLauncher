import QtQuick

/* Công tắc bật/tắt 36×20, trượt mượt. */
Rectangle {
    id: root
    property bool checked: true
    signal toggled(bool checked)

    width: 36; height: 20; radius: 10
    color: checked ? Theme.accent : Theme.border
    Behavior on color { ColorAnimation { duration: Theme.quick } }

    Rectangle {
        width: 16; height: 16; radius: 8
        y: 2
        x: root.checked ? root.width - width - 2 : 2
        color: "white"
        Behavior on x { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
    }
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.toggled(!root.checked) }
}
