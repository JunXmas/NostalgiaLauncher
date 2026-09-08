import QtQuick

/*
  Thẻ nổi trên ảnh hero, neo vào MỘT CÔNG TRÌNH trong ảnh: hành tinh, khối gỗ, khối đỏ.

  `landmarkX/Y` là toạ độ công trình tính theo phần trăm ảnh, nên đổi kích thước cửa sổ thì
  chấm neo vẫn đứng đúng chỗ. `pivot` là vị trí ƯU TIÊN của chấm neo trên bề ngang thẻ
  (0 = mép trái, 0.5 = giữa, 1 = mép phải). Thẻ không được tràn ra ngoài vùng trống của lớp
  cha (`freeRight`: mép trái cột HỒ SƠ); bị đẩy vào thì thẻ dịch, còn chấm neo vẫn đứng yên
  trên công trình — trước đây phải ghim `pivot: 1.0` cho hai thẻ bên phải để né cột, và ở màn
  hình rộng chúng lệch hẳn sang trái dù thừa chỗ.
*/
Item {
    id: root
    property string title: ""
    property string subtitle: ""
    property string glyph: ""
    property real landmarkX: 0.5
    property real landmarkY: 0.5
    property real pivot: 0.5
    property bool below: false
    property Item backdrop: null
    // Trang mà thẻ này dẫn tới. Để lộ ra ngoài để test đọc được đích của từng thẻ.
    property int pageIndex: 0
    signal activated()

    readonly property int cardHeight: 56
    readonly property int stemLength: 22
    readonly property real anchorX: parent.toPixelX(landmarkX)
    readonly property real anchorY: parent.toPixelY(landmarkY)

    width: row.width + 34
    height: cardHeight + stemLength
    x: Math.round(Math.max(0, Math.min(anchorX - width * pivot, parent.freeRight - width)))
    y: Math.round(anchorY - (below ? 0 : height))

    // Chấm neo trên công trình. Thở vài nhịp lúc hiện ra và khi rê chuột vào thẻ — không thở
    // mãi: một hoạt ảnh vô hạn bắt cả cửa sổ vẽ lại 144 lần/giây, ngốn ~19% CPU khi đứng yên.
    Rectangle {
        id: pin
        width: 10; height: 10; radius: 5
        x: Math.round(Math.min(Math.max(root.anchorX - root.x, 8), root.width - 8) - 5)
        y: root.below ? -5 : root.height - 5
        color: Theme.accent
        border.color: "#a0ffffff"
        border.width: 2
        SequentialAnimation on scale {
            id: pulse
            loops: 2
            NumberAnimation { to: 1.35; duration: 800; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0;  duration: 800; easing.type: Easing.InOutSine }
        }
    }
    Rectangle {
        width: 2
        height: root.stemLength - 4
        x: pin.x + 4
        y: root.below ? 4 : root.cardHeight
        color: "#b3ffffff"
    }

    Item {
        id: body
        width: parent.width
        height: root.cardHeight
        y: (root.below ? root.stemLength : 0) + (hover.hovered ? (root.below ? 3 : -3) : 0)
        scale: press.pressed ? 0.97 : (hover.hovered ? 1.04 : 1.0)
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        Glass {
            anchors.fill: parent
            backdrop: root.backdrop
            backdropRect: Qt.rect(root.x, root.y + body.y, width, height)
            borderColor: hover.hovered ? Theme.accent : "#1affffff"
            Behavior on borderColor { ColorAnimation { duration: Theme.quick } }
        }

        Row {
            id: row
            anchors.centerIn: parent
            spacing: 12

            Rectangle {
                width: 30; height: 30; radius: 7
                anchors.verticalCenter: parent.verticalCenter
                color: hover.hovered ? Theme.accent : Theme.accentDeep
                Behavior on color { ColorAnimation { duration: Theme.quick } }
                Text { anchors.centerIn: parent; text: root.glyph; color: "white"; font.pixelSize: 14 }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    text: root.title
                    color: Theme.text; font.pixelSize: 12; font.bold: true; font.letterSpacing: 0.8
                }
                Text { text: root.subtitle; color: Theme.textMuted; font.pixelSize: 10 }
            }
        }

        HoverHandler {
            id: hover
            cursorShape: Qt.PointingHandCursor
            onHoveredChanged: if (hovered) pulse.restart()
        }
        TapHandler { id: press; onTapped: root.activated() }
    }
}
