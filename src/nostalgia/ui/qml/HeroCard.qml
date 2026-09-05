import QtQuick

/*
  Thẻ nổi trên ảnh hero. Bấm được thật: mỗi thẻ đưa tới đúng trang của nó.

  Nền hơi trong suốt để thấy được cảnh phía sau, nhưng vẫn đủ đặc để chữ đọc rõ trên bất kỳ
  vùng ảnh nào — ảnh nền do người chơi chụp nên không thể biết trước chỗ đó sáng hay tối.
*/
Item {
    id: root
    property string title: ""
    property string subtitle: ""
    property string glyph: ""
    // Trang mà thẻ này dẫn tới. Để lộ ra ngoài để test đọc được đích của từng thẻ thay vì
    // phải bấm thử — bấm thử trong test thì chỉ biết "có gì đó xảy ra", không biết đúng chỗ.
    property int pageIndex: 0
    signal activated()

    implicitWidth: row.width + 34
    implicitHeight: 62

    Rectangle {
        id: body
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: hover.hovered ? "#f21c2620" : "#d9121a16"
        border.color: hover.hovered ? Theme.accent : "#4d3a4a40"
        border.width: 1
        scale: press.pressed ? 0.97 : (hover.hovered ? 1.04 : 1.0)
        y: hover.hovered ? -3 : 0

        Behavior on color { ColorAnimation { duration: Theme.quick } }
        Behavior on border.color { ColorAnimation { duration: Theme.quick } }
        Behavior on scale { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: Theme.quick; easing.type: Easing.OutCubic } }

        Row {
            id: row
            anchors.centerIn: parent
            spacing: 12

            Rectangle {
                width: 32; height: 32; radius: 7
                anchors.verticalCenter: parent.verticalCenter
                color: hover.hovered ? Theme.accent : Theme.accentDeep
                Behavior on color { ColorAnimation { duration: Theme.quick } }
                Text {
                    anchors.centerIn: parent
                    text: root.glyph; color: "white"; font.pixelSize: 15
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    text: root.title
                    color: Theme.text; font.pixelSize: 12; font.bold: true; font.letterSpacing: 0.8
                }
                Text {
                    text: root.subtitle
                    color: Theme.textMuted; font.pixelSize: 10
                }
            }
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: press; onTapped: root.activated() }
}
