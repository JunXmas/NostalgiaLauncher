import QtQuick

/*
  Thẻ nổi trên ảnh hero, neo vào MỘT CÔNG TRÌNH trong ảnh: nhà, cổng, bàn chế tác.

  `landmarkX/Y` là toạ độ công trình tính theo phần trăm ảnh, nên đổi kích thước cửa sổ thì
  thẻ vẫn đứng đúng chỗ. Chấm neo nằm ngay trên công trình, que nối dẫn lên (hoặc xuống) thẻ.
  `pivot` cho biết chấm neo rơi vào đâu trên bề ngang thẻ (0 = mép trái, 1 = mép phải) — dùng
  để hai thẻ cạnh nhau không đè lên nhau.
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

    width: row.width + 34
    height: cardHeight + stemLength
    x: Math.round(parent.toPixelX(landmarkX) - width * pivot)
    y: Math.round(parent.toPixelY(landmarkY) - (below ? 0 : height))

    // Chấm neo trên công trình, thở nhẹ để mắt bắt được.
    Rectangle {
        id: pin
        width: 10; height: 10; radius: 5
        x: Math.round(root.width * root.pivot - 5)
        y: root.below ? -5 : root.height - 5
        color: Theme.accent
        border.color: "#a0ffffff"
        border.width: 2
        SequentialAnimation on scale {
            loops: Animation.Infinite
            NumberAnimation { to: 1.35; duration: 1100; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0;  duration: 1100; easing.type: Easing.InOutSine }
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

        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { id: press; onTapped: root.activated() }
    }
}
