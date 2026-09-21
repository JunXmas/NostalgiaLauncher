import QtQuick

/*
  Công tắc kiểu Bedrock: ô VUÔNG hai nửa, núm sáng trượt ngang, nửa còn lại hiện ký hiệu
  `I` (bật) / `O` (tắt) — đúng ảnh mẫu. Cùng công thức khối với ActionButton: viền tối 2 px,
  cạnh dưới dày, mặt có vệt glint ở mép trên, bấm thì lún xuống.

  API giữ NGUYÊN như bản pill cũ (`checked`, `toggled(bool)`) để bốn chỗ gọi ở SettingsPage
  không phải sửa một dòng nào.
*/
Item {
    id: root
    property bool checked: true
    signal toggled(bool checked)

    readonly property int edge: 3                       // cạnh dưới "khối"
    readonly property int pressDrop: press.pressed ? 2 : 0
    readonly property color faceColor: root.checked ? Theme.blockOnFace : Theme.blockFace
    readonly property color edgeColor: root.checked ? Theme.blockOnEdge : Theme.blockEdge

    implicitWidth: 44; implicitHeight: 24
    width: implicitWidth; height: implicitHeight

    // Viền tối bao cả khối.
    Rectangle { anchors.fill: parent; color: Theme.blockBorder }
    // Cạnh dưới tối.
    Rectangle { anchors.fill: parent; anchors.margins: 2; color: root.edgeColor }
    // Mặt công tắc, lún xuống khi bấm.
    Rectangle {
        id: face
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 2 }
        anchors.topMargin: 2 + root.pressDrop
        height: parent.height - 4 - root.edge + root.pressDrop
        color: root.faceColor
        clip: true
        Behavior on color { ColorAnimation { duration: Theme.quick } }

        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top }
            height: 2; color: Theme.blockGlint
        }
        // Ô lõm chứa ký hiệu: nằm ở nửa KHÔNG có núm. Nền tối hơn mặt là chuyện tiếp cận,
        // không phải trang trí — trắng trên mặt xanh #3c8527 chỉ được 4,59:1, sát ngưỡng
        // WCAG 4,5:1; trên nền lõm này là 9,9:1 (xanh) và 14,0:1 (xám).
        Rectangle {
            objectName: "toggleWell"
            x: root.checked ? 0 : parent.width / 2
            width: parent.width / 2; height: parent.height
            color: root.edgeColor
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 2; color: "#40000000"
            }
        }
        // Ký hiệu nhảy thẳng sang nửa kia (không Behavior): núm trượt đè lên nó thì ký hiệu
        // phải biến mất khỏi chỗ cũ ngay, nếu không có một nhịp hai ký hiệu cùng hiện.
        Text {
            objectName: "toggleMark"
            x: root.checked ? 0 : parent.width / 2
            width: parent.width / 2; height: parent.height
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            text: root.checked ? "I" : "O"
            color: "white"
            font.pixelSize: 12; font.bold: true
            style: Text.Raised; styleColor: "#40000000"
        }
        // Núm: khối sáng vuông chiếm đúng một nửa, trượt sang phải khi bật.
        Rectangle {
            objectName: "toggleKnob"
            x: root.checked ? parent.width / 2 : 0
            width: parent.width / 2; height: parent.height
            color: hover.hovered ? "#e8e9ea" : Theme.blockLight
            Behavior on x { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: Theme.quick } }
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 2; color: "#88ffffff"
            }
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 2; color: "#33000000"
            }
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: press; onTapped: root.toggled(!root.checked) }
}
