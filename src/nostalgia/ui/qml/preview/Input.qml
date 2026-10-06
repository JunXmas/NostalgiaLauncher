import QtQuick

Rectangle {
    id: root
    property alias text: field.text
    property alias echoMode: field.echoMode
    property string placeholder: ""
    signal accepted
    function focusInput() {
        field.forceActiveFocus();
    }
    height: 46 * GlassTheme.scale
    radius: 12
    color: "#7010181d"
    border.color: field.activeFocus ? GlassTheme.accent : GlassTheme.stroke
    TextInput {
        id: field
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        verticalAlignment: TextInput.AlignVCenter
        font.family: GlassTheme.font
        font.pixelSize: 14 * GlassTheme.scale
        color: GlassTheme.text
        selectByMouse: true
        clip: true
        activeFocusOnTab: true
        Accessible.name: root.placeholder
        Accessible.role: Accessible.EditableText
        onAccepted: root.accepted()
    }
    Text {
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        visible: !field.text.length
        text: root.placeholder
        font.family: GlassTheme.font
        font.pixelSize: 14 * GlassTheme.scale
        color: GlassTheme.muted
    }
}
