import QtQuick

Rectangle {
    id: card
    objectName: "roomSyncCard"
    property bool hostMode: false
    readonly property var info: roomSyncBridge.offer
    implicitHeight: content.implicitHeight + 28
    height: implicitHeight
    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.14)
    radius: Theme.radiusSmall
    border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.4)
    Column {
        id: content
        x: 14; y: 14; width: parent.width - 28; spacing: 10
        Text {
            width: parent.width; wrapMode: Text.WordWrap
            text: card.hostMode ? "Đồng bộ modpack · Plus" : "Đồng bộ modpack với chủ phòng"
            color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true
        }
        Text {
            width: parent.width; wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: card.hostMode
                ? "Một người có Plus, cả nhóm cùng chơi. Chọn đúng bản đang mở LAN; bạn bè nhận lời mời được đồng bộ miễn phí."
                : (card.info.name || "") + "\nMinecraft " + (card.info.gameVersion || "") + " · " + (card.info.loader || "") + " " + (card.info.loaderVersion || "") + "\n" + (card.info.fileCount || 0) + " file · " + ((card.info.sizeMiB || 0) === 0 ? "<0,1" : card.info.sizeMiB) + " MiB"
            color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.25
        }
        Dropdown {
            id: packChoice
            objectName: "roomPackChoice"
            visible: card.hostMode; width: parent.width
            model: bridge.instances.map(function(instance) { return instance.label; })
            currentIndex: model.length ? 0 : -1
        }
        Text {
            visible: card.hostMode && !roomSyncBridge.canShare
            width: parent.width; wrapMode: Text.WordWrap
            text: roomSyncBridge.configured ? "Relay hiện chưa cấp vé Plus. Tính năng sẽ mở khi backend được cấu hình." : "Bản preview chưa nối dịch vụ Plus. Chơi chung thường vẫn hoạt động."
            color: Theme.textMuted; font.pixelSize: Theme.fontBody
        }
        Text {
            visible: !card.hostMode; width: parent.width; wrapMode: Text.WordWrap
            text: "Tạo bản chơi riêng, giữ nguyên modpack hiện có. Chỉ nhận mod từ chủ phòng bạn tin tưởng."
            color: Theme.textMuted; font.pixelSize: Theme.fontBody
        }
        ActionButton {
            objectName: card.hostMode ? "shareRoomPackButton" : "syncRoomPackButton"
            width: parent.width
            label: roomSyncBridge.busy ? "Đang xử lý..." : (card.hostMode ? "Chia sẻ modpack cho phòng" : "Đồng bộ vào bản chơi mới · Miễn phí")
            clickable: !roomSyncBridge.busy && (card.hostMode ? roomSyncBridge.canShare && packChoice.currentIndex >= 0 : true)
            onClicked: {
                if (card.hostMode) roomSyncBridge.publish(bridge.instances[packChoice.currentIndex].instanceId);
                else roomSyncBridge.sync();
            }
        }
        ActionButton {
            visible: roomSyncBridge.busy; primary: false; label: "Huỷ đồng bộ"
            onClicked: roomSyncBridge.cancel()
        }
        Text {
            visible: roomSyncBridge.note !== ""; width: parent.width; wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: roomSyncBridge.note; color: Theme.text; font.pixelSize: Theme.fontBody
        }
    }
}
