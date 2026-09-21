import QtQuick

/* Hộp chọn một mục: bấm mở danh sách ngay dưới (hoặc trên), chọn xong tự đóng. `model` là mảng
   chuỗi. Dùng MouseArea chứ không TapHandler cho các hàng và nền khay: TapHandler không nuốt sự
   kiện, nên bấm một hàng đè lên nút CHƠI là nút CHƠI cũng nhận cú bấm (lỗi thật). */
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
    // Nhãn phụ ở trạng thái ĐÓNG (vd "3 bản"): hộp đóng chỉ hiện một dòng, nên không có nó
    // người dùng tưởng danh sách chỉ có đúng một mục.
    property string badge: ""
    // Nhãn ghim vào ĐÚNG một hàng trong khay (vd "vừa chơi"). Để riêng chứ không nối vào
    // chuỗi `model`: tên bản chơi dài bị elide sẽ nuốt mất nhãn, đúng lúc cần nó nhất.
    property int markedIndex: -1
    property string markLabel: ""
    signal activated(int index)
    // Khay treo lên contentItem của cửa sổ (lớp trên cùng) chứ không nằm trong cây của hộp:
    // nằm trong cây thì thứ tự vẽ của cha (vd cột nút CHƠI) quyết định, và các hàng đè lên thẻ
    // hero từng bị thẻ hero hứng mất cú bấm. Toạ độ tính lại mỗi lần mở.
    property point origin: Qt.point(0, 0)
    onOpenChanged: if (open) origin = root.mapToItem(null, 0, 0)

    height: 34

    Rectangle {
        id: head
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: hover.containsMouse || root.open ? Theme.surfaceHigh : Theme.surface
        border.color: root.open ? Theme.accent : Theme.border
        border.width: 1
        Behavior on color { ColorAnimation { duration: Theme.quick } }

        Text {
            anchors { left: parent.left; leftMargin: 11; right: badgePill.left; rightMargin: 8; verticalCenter: parent.verticalCenter }
            text: root.currentText || root.placeholder
            color: root.currentText ? Theme.text : Theme.textMuted
            font.pixelSize: 12; elide: Text.ElideRight
        }
        Rectangle {
            id: badgePill
            objectName: "dropdownBadge"
            visible: root.badge.length > 0
            anchors { right: arrow.left; rightMargin: visible ? 8 : 0; verticalCenter: parent.verticalCenter }
            width: visible ? badgeText.width + 14 : 0
            height: 20
            radius: 10
            color: Theme.accentSoft
            border.color: Theme.border
            Text {
                id: badgeText
                anchors.centerIn: parent
                text: root.badge
                color: Theme.accent; font.pixelSize: 11; font.bold: true
            }
        }
        Text {
            id: arrow
            anchors { right: parent.right; rightMargin: 11; verticalCenter: parent.verticalCenter }
            text: "⌄"; color: Theme.textMuted; font.pixelSize: 14
            rotation: (root.open !== root.dropUp) ? 180 : 0
            Behavior on rotation { NumberAnimation { duration: Theme.quick } }
        }
        MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: root.open = !root.open
        }
    }

    Rectangle {
        id: popup
        objectName: "dropdownPopup"
        parent: root.Window.window ? root.Window.window.contentItem : root
        z: 1000
        width: root.width
        x: root.origin.x
        y: root.origin.y + (root.dropUp ? -height - 4 : head.height + 4)
        height: root.open ? Math.min(root.model.length, 8) * 32 + 8 : 0
        visible: height > 0
        clip: true
        radius: Theme.radiusSmall
        color: Theme.surfaceHigh
        border.color: Theme.border
        border.width: 1
        Behavior on height { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent }  // nuốt bấm vào khe/viền khay, không lọt xuống dưới

        ListView {
            anchors { fill: parent; margins: 4 }
            model: root.model
            clip: true
            delegate: Rectangle {
                width: ListView.view.width
                height: 32
                radius: 6
                color: rowHover.containsMouse ? Theme.accentSoft : "transparent"
                Text {
                    anchors {
                        left: parent.left; leftMargin: 8
                        right: mark.left; rightMargin: 8
                        verticalCenter: parent.verticalCenter
                    }
                    text: modelData
                    color: index === root.currentIndex ? Theme.accent : Theme.text
                    font.pixelSize: 12; elide: Text.ElideRight
                }
                Text {
                    id: mark
                    objectName: "dropdownMark"
                    visible: index === root.markedIndex && root.markLabel.length > 0
                    width: visible ? implicitWidth : 0
                    anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                    text: root.markLabel
                    color: Theme.accent; font.pixelSize: 11; font.bold: true
                }
                MouseArea {
                    id: rowHover
                    anchors.fill: parent
                    hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: { root.currentIndex = index; root.open = false; root.activated(index); }
                }
            }
        }
    }
}
