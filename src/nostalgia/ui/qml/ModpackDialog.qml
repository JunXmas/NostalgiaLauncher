import QtQuick

/* Hộp đặt tên bản chơi khi cài modpack. Tên trống thì lấy tên pack. */
Item {
    id: dialog
    visible: false
    z: 100
    property string projectId: ""
    property string packTitle: ""

    function openFor(id, title) { projectId = id; packTitle = title; nameField.text = ""; visible = true; }

    MouseArea {
        anchors.fill: parent
        onClicked: dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 460; height: 230
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        MouseArea { anchors.fill: parent }

        Column {
            anchors { fill: parent; margins: 26 }
            spacing: 14
            Text { text: "Cài modpack thành bản chơi"; color: Theme.text; font.pixelSize: 18; font.bold: true }
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: dialog.packTitle + " sẽ thành một bản chơi mới với đúng loader và phiên bản mà pack yêu cầu. Có thể mất vài phút."
                color: Theme.textMuted; font.pixelSize: 12
            }
            TextField { id: nameField; width: parent.width; placeholder: dialog.packTitle }
            Row {
                spacing: 8
                ActionButton {
                    label: "Cài"
                    onClicked: { contentBridge.installModpack(dialog.projectId, nameField.text); dialog.visible = false; }
                }
                ActionButton { primary: false; label: "Huỷ"; onClicked: dialog.visible = false }
            }
        }
    }
}
