import QtQuick
import QtQuick.Dialogs

/* Hộp đặt tên bản chơi khi cài modpack. Tên trống thì lấy tên pack. */
Item {
    id: dialog
    visible: false
    z: 100
    property string projectId: ""
    property string packTitle: ""
    property string gameDirUrl: ""
    readonly property string gameDirPath: gameDirUrl ? decodeURIComponent(String(gameDirUrl).replace(/^file:\/\//, "")) : ""

    function openFor(id, title) { projectId = id; packTitle = title; nameField.text = ""; gameDirUrl = ""; visible = true; }

    MouseArea {
        anchors.fill: parent
        onClicked: dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 460; height: 290
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
                    primary: false; label: "📁  Thư mục chơi"
                    onClicked: folderPicker.open()
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 260; elide: Text.ElideMiddle
                    text: dialog.gameDirUrl ? dialog.gameDirPath : "mặc định"
                    color: dialog.gameDirUrl ? Theme.text : Theme.textMuted; font.pixelSize: 11
                }
            }
            Row {
                spacing: 8
                ActionButton {
                    label: "Cài"
                    onClicked: { contentBridge.installModpack(dialog.projectId, nameField.text, dialog.gameDirUrl); dialog.visible = false; }
                }
                ActionButton { primary: false; label: "Huỷ"; onClicked: dialog.visible = false }
            }
        }
    }

    FolderDialog {
        id: folderPicker
        title: "Chọn thư mục chơi cho modpack này"
        onAccepted: dialog.gameDirUrl = selectedFolder.toString()
    }
}
