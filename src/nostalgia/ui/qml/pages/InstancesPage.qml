import QtQuick
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
        ActionButton {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            label: "+  Tạo mới"
            onClicked: dialog.openDialog()
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
                    playable: bridge.activePlayerName.length > 0 && !bridge.busy
                    onPlayRequested: bridge.play(modelData.instanceId)
                    onRemoveRequested: bridge.removeInstance(modelData.instanceId)
                }
            }
        }
    }

    CreateInstanceDialog { id: dialog; objectName: "createDialog"; anchors.fill: parent }
}
