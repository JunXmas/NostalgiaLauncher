import QtQuick

/* Hộp kiểm + nhãn, dùng trong cột lọc. */
Item {
    id: root
    property string label: ""
    property bool checked: false
    signal toggled(bool checked)

    // Rộng theo nội dung. KHÔNG lấy `parent.width`: đặt trong `Row` thì Row rộng theo con và con
    // rộng theo Row → vòng lặp polish vô hạn (1.280 cảnh báo trong một phiên, CPU quay không).
    // Chỗ nào muốn kéo hết bề ngang (cột lọc) thì tự đặt `width: parent.width`.
    implicitWidth: box.width + 9 + caption.implicitWidth
    width: implicitWidth
    height: 26

    Rectangle {
        id: box
        width: 16; height: 16; radius: 4
        anchors { left: parent.left; verticalCenter: parent.verticalCenter }
        color: root.checked ? Theme.accent : "transparent"
        border.color: root.checked ? Theme.accent : Theme.textMuted
        border.width: 1
        Behavior on color { ColorAnimation { duration: Theme.quick } }
        Text {
            anchors.centerIn: parent
            visible: root.checked
            text: "✓"; color: "#06210f"; font.pixelSize: 11; font.bold: true
        }
    }
    Text {
        id: caption
        anchors { left: box.right; leftMargin: 9; right: parent.right; verticalCenter: parent.verticalCenter }
        text: root.label
        color: root.checked ? Theme.text : Theme.textMuted
        font.pixelSize: 12; elide: Text.ElideRight
    }
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.toggled(!root.checked) }
}
