import QtQuick
import "preview" as Preview
import QtQuick.Dialogs

/* Hộp đặt tên bản chơi khi cài modpack. Tên trống thì lấy tên pack. */
Item {
    id: dialog
    visible: false
    z: 100
    Keys.onEscapePressed: dialog.visible = false
    property string projectId: ""
    property string packTitle: ""
    property string gameDirUrl: ""
    readonly property string gameDirPath: gameDirUrl ? decodeURIComponent(String(gameDirUrl).replace(/^file:\/\//, "")) : ""

    function openFor(id, title) { projectId = id; packTitle = title; nameField.text = ""; gameDirUrl = ""; visible = true; box.forceActiveFocus(); }

    MouseArea {
        anchors.fill: parent
        onWheel: function(event) { event.accepted = true; }
        onClicked: dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    DialogFrame {
        id: box
        objectName: "ModpackDialogSurface"
        anchors.centerIn: parent
        width: Math.min(Theme.modern ? 620 * Theme.textScale : 460, parent.width - 40)
        height: Math.min(packColumn.implicitHeight + 52, parent.height - 40)
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        MouseArea { anchors.fill: parent }

        Preview.InertialScroll {
            id: packFormScroll
            objectName: "packFormScroll"
            anchors.fill: parent; anchors.margins: 26
            contentHeight: packColumn.implicitHeight
        Column {
            id: packColumn
            width: packFormScroll.width
            spacing: 14
            Text { text: Tr.phrase("Cài modpack thành bản chơi"); color: Theme.text; font.family: Theme.modern ? "Manrope" : Theme.sans; font.pixelSize: Theme.fontTitle; font.bold: true }
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: dialog.packTitle + Tr.phrase(" sẽ thành một bản chơi mới với đúng loader và phiên bản mà pack yêu cầu. Có thể mất vài phút.")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody
            }
            TextField { id: nameField; width: parent.width; placeholder: dialog.packTitle }
            Flow {
                width: parent.width; spacing: 8
                ActionButton {
                    primary: false; label: Tr.phrase("📁  Thư mục chơi")
                    onClicked: folderPicker.open()
                }
                Text {
                    height: Math.max(36, Theme.fontBody + 22)
                    verticalAlignment: Text.AlignVCenter
                    width: Math.min(260 * Theme.textScale, packColumn.width); elide: Text.ElideMiddle
                    text: dialog.gameDirUrl ? dialog.gameDirPath : Tr.phrase("mặc định")
                    color: dialog.gameDirUrl ? Theme.text : Theme.textMuted; font.pixelSize: Theme.fontBody
                }
            }
            Flow {
                width: parent.width; spacing: 8
                ActionButton {
                    objectName: "quickModpackInstall"
                    label: Tr.phrase("Cài")
                    onClicked: { contentBridge.installModpack(dialog.projectId, nameField.text, dialog.gameDirUrl); dialog.visible = false; }
                }
                ActionButton { primary: false; label: Tr.phrase("Huỷ"); onClicked: dialog.visible = false }
            }
        }
        }
    }

    FolderDialog {
        id: folderPicker
        title: Tr.phrase("Chọn thư mục chơi cho modpack này")
        onAccepted: dialog.gameDirUrl = selectedFolder.toString()
    }
}
