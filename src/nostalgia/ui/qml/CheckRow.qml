import QtQuick

/* Hộp kiểm + nhãn, dùng trong cột lọc. Khối kiểu Bedrock như ActionButton/Toggle: viền
   tối, mặt sáng, cạnh dưới dày, bấm thì lún xuống.

   Dấu tick NHẢY RA: phóng quá cỡ rồi co về 1 (OutBack), nên mắt bắt được là "vừa có thứ
   xuất hiện" chứ không phải "khung hình này khác khung trước". Bỏ tick thì co nhanh về 0,
   không nảy — nảy lúc biến mất trông như lỗi vẽ. */
Item {
    id: root
    property string label: ""
    property bool checked: false
    signal toggled(bool checked)
    // Cỡ hiện tại của dấu tick, lộ ra để test lấy mẫu giữa chừng hoạt ảnh. Đi vòng qua
    // cây con (children[0].children[3]) thì đổi thứ tự một Rectangle là test đỏ oan.
    readonly property real tickScale: tick.scale

    // Rộng theo nội dung. KHÔNG lấy `parent.width`: đặt trong `Row` thì Row rộng theo con và con
    // rộng theo Row → vòng lặp polish vô hạn (1.280 cảnh báo trong một phiên, CPU quay không).
    // Chỗ nào muốn kéo hết bề ngang (cột lọc) thì tự đặt `width: parent.width`.
    implicitWidth: box.width + 9 + caption.implicitWidth
    width: implicitWidth
    height: 26

    readonly property int edge: 3                    // cạnh dưới "khối"
    readonly property int pressDrop: press.pressed ? 2 : 0

    Item {
        id: box
        width: 18; height: 18
        anchors { left: parent.left; verticalCenter: parent.verticalCenter }

        Rectangle { anchors.fill: parent; color: Theme.blockBorder }
        Rectangle {
            anchors.fill: parent; anchors.margins: 2
            color: root.checked ? Theme.blockOnEdge : Theme.blockEdge
            Behavior on color { ColorAnimation { duration: Theme.quick } }
        }
        Rectangle {
            id: face
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 2 }
            anchors.topMargin: 2 + root.pressDrop
            height: parent.height - 4 - root.edge + root.pressDrop
            color: root.checked ? Theme.blockOnFace
                                : (hover.hovered ? "#5a5c5e" : Theme.blockFace)
            Behavior on color { ColorAnimation { duration: Theme.quick } }
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 2; color: Theme.blockGlint
            }
        }

        Text {
            id: tick
            objectName: "checkTick"
            anchors.centerIn: face
            text: "✓"
            color: "white"
            font.pixelSize: Theme.fontHeading; font.bold: true
            style: Text.Raised; styleColor: "#60000000"
            // Bắt đầu ở 0 và để hoạt ảnh đẩy lên: nếu để 1 rồi mới thu về, khung hình đầu
            // tiên đã kịp hiện một dấu tick to đùng.
            scale: 0
            // Quay nhẹ theo cỡ: lúc phóng to thì nghiêng, về chỗ thì thẳng. Đây là chỗ MSAA
            // thực sự có việc — cạnh nghiêng của glyph không nằm trên lưới pixel.
            rotation: (1 - scale) * -18
            visible: scale > 0.01

            states: State {
                name: "hien"; when: root.checked
                PropertyChanges { target: tick; scale: 1 }
            }
            transitions: [
                // Bật: vọt quá 1 rồi về — OutBack lo đoạn vọt, không phải tự đếm khung.
                Transition {
                    to: "hien"
                    NumberAnimation {
                        property: "scale"; duration: Theme.normal
                        easing.type: Easing.OutBack; easing.overshoot: 3.4
                    }
                },
                // Tắt: co thẳng, không nảy.
                Transition {
                    from: "hien"
                    NumberAnimation {
                        property: "scale"; duration: Theme.quick; easing.type: Easing.InQuad
                    }
                }
            ]
        }
    }

    Text {
        id: caption
        anchors { left: box.right; leftMargin: 9; right: parent.right; verticalCenter: parent.verticalCenter }
        text: root.label
        color: root.checked ? Theme.text : Theme.textMuted
        font.pixelSize: Theme.fontBody; elide: Text.ElideRight
        Behavior on color { ColorAnimation { duration: Theme.quick } }
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: press; onTapped: root.toggled(!root.checked) }
}
