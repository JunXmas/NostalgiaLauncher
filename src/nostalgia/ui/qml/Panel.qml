import QtQuick

/* Khung thẻ dùng chung cho mọi ô ở cột phải và ô danh sách bản chơi. */
Rectangle {
    default property alias content: holder.data
    property string title: ""
    property string action: ""
    signal actionClicked()

    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.border
    border.width: 1

    Text {
        id: heading
        visible: title.length > 0
        anchors { top: parent.top; left: parent.left; margins: Theme.pad }
        text: title
        color: Theme.accent
        font.pixelSize: 12
        font.bold: true
        font.letterSpacing: 1.2
    }

    Text {
        visible: action.length > 0
        anchors { top: parent.top; right: parent.right; margins: Theme.pad }
        text: action
        color: link.hovered ? Theme.accent : Theme.textMuted
        font.pixelSize: 11
        Behavior on color { ColorAnimation { duration: Theme.quick } }
        HoverHandler { id: link; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: actionClicked() }
    }

    Item {
        id: holder
        anchors {
            top: heading.visible ? heading.bottom : parent.top
            topMargin: heading.visible ? 14 : Theme.pad
            left: parent.left; right: parent.right; bottom: parent.bottom
            leftMargin: Theme.pad; rightMargin: Theme.pad; bottomMargin: Theme.pad
        }
    }
}
