import QtQuick

/* Ô nhập một dòng, viền sáng lên khi đang gõ. */
Rectangle {
    id: root
    property alias text: input.text
    property alias echoMode: input.echoMode
    property string placeholder: ""
    signal accepted()
    function focusInput() { input.forceActiveFocus(); }

    height: Math.max(34, Theme.fontBody + 18)
    radius: Theme.radiusSmall
    color: Theme.modern ? Qt.rgba(Theme.surfaceHigh.r, Theme.surfaceHigh.g, Theme.surfaceHigh.b, 0.65) : Theme.surfaceHigh
    border.color: input.activeFocus ? Theme.accent : Theme.border
    border.width: 1
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }

    TextInput {
        id: input
        anchors { fill: parent; leftMargin: 11; rightMargin: 11 }
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.text
        font.family: Theme.sans
        font.pixelSize: Theme.fontBody
        clip: true
        selectByMouse: true
        activeFocusOnTab: true
        Accessible.role: Accessible.EditableText
        Accessible.name: root.placeholder
        onAccepted: root.accepted()
    }
    Text {
        anchors { left: parent.left; leftMargin: 11; verticalCenter: parent.verticalCenter }
        visible: input.text.length === 0
        text: root.placeholder
        color: Theme.textMuted; font.family: Theme.sans
        font.pixelSize: Theme.fontBody
    }
}
