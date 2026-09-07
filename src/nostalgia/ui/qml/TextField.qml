import QtQuick

/* Ô nhập một dòng, viền sáng lên khi đang gõ. */
Rectangle {
    id: root
    property alias text: input.text
    property alias echoMode: input.echoMode
    property string placeholder: ""
    signal accepted()

    height: 34
    radius: Theme.radiusSmall
    color: Theme.surfaceHigh
    border.color: input.activeFocus ? Theme.accent : Theme.border
    border.width: 1
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }

    TextInput {
        id: input
        anchors { fill: parent; leftMargin: 11; rightMargin: 11 }
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.text
        font.pixelSize: 12
        clip: true
        selectByMouse: true
        onAccepted: root.accepted()
    }
    Text {
        anchors { left: parent.left; leftMargin: 11; verticalCenter: parent.verticalCenter }
        visible: input.text.length === 0
        text: root.placeholder
        color: Theme.textMuted; font.pixelSize: 12
    }
}
