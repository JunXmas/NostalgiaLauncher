import QtQuick

/* Nút phụ: dùng cho "Thêm tài khoản", "Tạo mới", "Tải phiên bản". */
Rectangle {
    id: root
    property string label: ""
    property bool primary: true
    property bool clickable: true
    signal clicked()

    height: 34
    implicitWidth: caption.width + 30
    radius: Theme.radiusSmall
    color: !root.clickable ? Theme.surfaceHigh
           : root.primary ? (hover.hovered ? Theme.accent : Theme.accentDeep)
                          : (hover.hovered ? Theme.surfaceHigh : Theme.surface)
    border.color: root.primary ? "transparent" : Theme.border
    border.width: root.primary ? 0 : 1
    Behavior on color { ColorAnimation { duration: Theme.quick } }

    Text {
        id: caption
        anchors.centerIn: parent
        text: root.label
        color: !root.clickable ? Theme.textMuted : (root.primary ? "white" : Theme.text)
        font.pixelSize: 12; font.bold: root.primary
    }

    HoverHandler { id: hover; enabled: root.clickable; cursorShape: Qt.PointingHandCursor }
    TapHandler { enabled: root.clickable; onTapped: root.clicked() }
}
