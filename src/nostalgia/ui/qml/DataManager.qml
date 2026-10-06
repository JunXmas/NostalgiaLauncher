import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Dialogs

Item {
    id: root
    objectName: "dataManager"
    visible: false; z: 120
    property string statusMessage: ""
    Connections { target: storageBridge; function onCompleted(message) { root.statusMessage = message; } }
    property string selectedBackup: ""
    function openDialog() { storageBridge.refresh(); root.visible = true; root.forceActiveFocus(); }
    Keys.onEscapePressed: root.visible = false
    Rectangle { anchors.fill: parent; color: "#c0000000"; MouseArea { anchors.fill: parent } }
    DialogFrame {
        id: box
        anchors.centerIn: parent
        width: Math.min(900, parent.width - 48); height: Math.min(650, parent.height - 48)
        radius: Theme.radius; color: Theme.surface; border.color: Theme.border
        MouseArea { anchors.fill: parent }
        Column {
            anchors.fill: parent; anchors.margins: 20; spacing: 14
            Row {
                width: parent.width; spacing: 18
                Text { text: Tr.phrase("Sao lưu & thùng rác"); color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true; width: parent.width - 110 }
                ActionButton { primary: false; label: Tr.phrase("Đóng"); onClicked: root.visible = false }
            }
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: Tr.phrase("Sao lưu gồm save, mods và config. Khôi phục tạo bản chơi mới; kho game và Java dùng chung.")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody
            }
            Flow {
                width: parent.width; spacing: 10
                ActionButton { primary: false; label: Tr.phrase("Mở thư mục sao lưu"); onClicked: storageBridge.openBackupsFolder() }
                ActionButton { primary: false; label: Tr.phrase("Chọn file sao lưu…"); onClicked: picker.open() }
            }
            Controls.ScrollView {
                width: parent.width; height: Math.max(70, box.height - 340 * Theme.textScale)
                clip: true; contentWidth: availableWidth
                Column {
                    width: parent.width; spacing: 10
                    SectionTitle { caption: Tr.phrase("Bản sao lưu") }
                    Text { visible: storageBridge.backups.length === 0; text: Tr.phrase("Chưa có bản sao lưu. Bấm Sao lưu trên một bản chơi."); color: Theme.textMuted; font.pixelSize: Theme.fontBody }
                    Repeater {
                        model: storageBridge.backups
                        ActionButton {
                            width: parent.width; primary: root.selectedBackup === modelData.path
                            label: modelData.label + " · " + modelData.created + " · " + modelData.size
                            onClicked: { root.selectedBackup = modelData.path; restoreName.text = "restore-" + Date.now(); }
                        }
                    }
                    SectionTitle { caption: Tr.phrase("Thùng rác") }
                    Text { visible: storageBridge.trash.length === 0; text: Tr.phrase("Thùng rác trống."); color: Theme.textMuted; font.pixelSize: Theme.fontBody }
                    Repeater {
                        model: storageBridge.trash
                        Row {
                            width: parent.width; spacing: 10
                            Text { text: modelData.label; width: parent.width - 155; elide: Text.ElideRight; color: Theme.text; font.pixelSize: Theme.fontBody; anchors.verticalCenter: parent.verticalCenter }
                            ActionButton { label: Tr.phrase("Khôi phục"); clickable: !storageBridge.busy; onClicked: storageBridge.restoreTrash(modelData.trashId) }
                        }
                    }
                }
            }
            Text { width: parent.width; wrapMode: Text.WordWrap; visible: root.statusMessage.length > 0; text: root.statusMessage; color: Theme.brand; font.pixelSize: Theme.fontBody }
            Text { text: storageBridge.busy ? Tr.phrase("Đang xử lý…") : Tr.phrase("Mã bản chơi mới khi khôi phục"); color: Theme.textMuted; font.pixelSize: Theme.fontBody }
            Flow {
                width: parent.width; spacing: 10
                TextField { id: restoreName; objectName: "restoreName"; width: Math.min(300, parent.width); placeholder: "restore-01" }
                ActionButton { objectName: "restoreBackupButton"; label: Tr.phrase("Khôi phục sang bản mới"); clickable: !storageBridge.busy && root.selectedBackup.length > 0 && /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(restoreName.text); onClicked: storageBridge.restoreBackup(root.selectedBackup,restoreName.text) }
            }
        }
    }
    FileDialog {
        id: picker; title: Tr.phrase("Chọn bản sao lưu Nostalgia"); nameFilters: ["Nostalgia backup (*.zip)"]
        onAccepted: { root.selectedBackup = String(selectedFile); restoreName.text = "restore-" + Date.now(); }
    }
}
