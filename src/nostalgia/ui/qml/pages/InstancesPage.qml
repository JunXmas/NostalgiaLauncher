import QtQuick
import QtQuick.Dialogs
import "../"

/* Trang BẢN CHƠI: lưới thẻ, nút tạo mới mở hộp thoại hai cột, gỡ bằng nút trên thẻ. */
Item {
    id: page
    signal navigate(int pageIndex)

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 66
        Column {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            spacing: 3
            Text { text: "Bản chơi"; color: Theme.text; font.pixelSize: 24; font.bold: true }
            Text {
                text: bridge.instances.length + " bản chơi  ·  mỗi bản một thư mục riêng, kho tải dùng chung"
                color: Theme.textMuted; font.pixelSize: 12
            }
        }
        Row {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            spacing: 8
            ActionButton {
                primary: false
                label: "Nhập modpack từ file"
                clickable: !bridge.busy && !contentBridge.busy
                onClicked: packPicker.open()
            }
            ActionButton {
                label: "+  Tạo mới"
                onClicked: dialog.openDialog()
            }
        }
    }

    Panel {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: 0 }

        Text {
            visible: bridge.instances.length === 0
            text: "Chưa có bản chơi nào. Bấm “Tạo mới” để chọn phiên bản và loader."
            color: Theme.textMuted; font.pixelSize: 12
        }

        Grid {
            id: grid
            anchors { left: parent.left; right: parent.right; top: parent.top }
            readonly property int cardHeight: 168
            columns: 4
            spacing: Theme.gap
            Repeater {
                model: bridge.instances
                InstanceCard {
                    width: Math.floor((grid.width - (grid.columns - 1) * Theme.gap) / grid.columns)
                    height: grid.cardHeight
                    label: modelData.label
                    versionId: modelData.versionId
                    removable: true
                    editable: true
                    iconUrl: modelData.iconUrl || ""
                    playable: bridge.activePlayerName.length > 0 && !bridge.busy
                    onPlayRequested: bridge.play(modelData.instanceId)
                    onRemoveRequested: bridge.removeInstance(modelData.instanceId)
                    onEditRequested: editDialog.openFor(modelData)
                }
            }
        }
    }

    CreateInstanceDialog { id: dialog; objectName: "createDialog"; anchors.fill: parent }
    InstanceEditDialog { id: editDialog; anchors.fill: parent }

    // Modpack từ file trên máy: .mrpack (Modrinth) hoặc .zip (CurseForge); nhận dạng theo nội dung.
    FileDialog {
        id: packPicker
        title: "Chọn modpack"
        nameFilters: ["Modpack (*.mrpack *.zip)", "Mọi file (*)"]
        onAccepted: contentBridge.importModpackFile(selectedFile.toString(), "")
    }
}
