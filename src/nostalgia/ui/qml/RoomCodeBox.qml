import QtQuick

/* Một ô 6 ký tự của mã phòng. TextInput trong suốt nhận phím; sáu ô chữ bên dưới vẽ từng ký
   tự và lật như xúc xắc khi ký tự đổi. Dùng trong `RoomCodeInput`, gọi ngược `parent.digest`
   và `parent.backspace`. */
Rectangle {
    id: box
    property int position: 0
    property alias text: input.text
    readonly property bool focused: input.activeFocus  // `activeFocus` của Item là FINAL, không đè được
    function focusInput() { input.forceActiveFocus(); }

    width: 108; height: 46
    radius: Theme.radiusSmall
    color: Theme.surfaceHigh
    border.color: input.activeFocus ? Theme.accent : Theme.border
    border.width: 1
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }

    Row {
        anchors.centerIn: parent
        spacing: 2
        Repeater {
            model: box.parent.groupLength
            Item {
                id: cell
                required property int index
                readonly property string character: input.text.charAt(index)
                width: 15; height: 28
                onCharacterChanged: if (character.length > 0) flip.restart()

                Text {
                    id: glyph
                    anchors.centerIn: parent
                    text: cell.character.length > 0 ? cell.character : "·"
                    color: cell.character.length > 0 ? Theme.text : Theme.textMuted
                    font.pixelSize: 20; font.bold: true; font.family: "monospace"
                    transform: Rotation { id: tilt; origin.x: glyph.width / 2; origin.y: glyph.height / 2; axis { x: 1; y: 0; z: 0 } }
                }
                SequentialAnimation {
                    id: flip
                    PropertyAction { target: tilt; property: "angle"; value: -90 }
                    NumberAnimation { target: tilt; property: "angle"; to: 0; duration: Theme.normal; easing.type: Easing.OutBack }
                }
            }
        }
    }

    TextInput {
        id: input
        anchors.fill: parent
        color: "transparent"; cursorVisible: false
        selectByMouse: false
        onTextChanged: box.parent.digest(box.position)
        onAccepted: box.parent.submitted()
        Keys.onPressed: function (event) { box.parent.backspace(box.position, event); }
    }
    HoverHandler { cursorShape: Qt.IBeamCursor }
}
