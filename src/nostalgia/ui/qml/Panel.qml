import QtQuick

/* Khung thẻ dùng chung cho mọi ô ở cột phải và ô danh sách bản chơi. */
Rectangle {
    default property alias content: holder.data
    property string title: ""
    // Nằm trên ảnh nền thì để lộ ảnh phía sau một chút, như tấm kính.
    property bool translucent: false
    // Mép trên của vùng nội dung (dưới tiêu đề), để thẻ nào cao theo nội dung tính được chiều cao.
    readonly property alias contentTop: holder.y

    color: translucent ? "#d90f1512" : Theme.surface
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
