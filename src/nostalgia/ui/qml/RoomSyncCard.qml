import QtQuick

Rectangle {
    id: card
    objectName: "roomSyncCard"
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
            text: Tr.phrase("Đồng bộ modpack với chủ phòng")
            color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true
        }
        Text {
            width: parent.width; wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: (card.info.name || "") + "\nMinecraft " + (card.info.gameVersion || "") + " · " + (card.info.loader || "") + " " + (card.info.loaderVersion || "") + "\n" + (card.info.basePack ? Tr.phrase("Pack gốc: ") + card.info.basePack + " · " + (card.info.additionalMods || 0) + Tr.phrase(" mod bổ sung/thay đổi\n") : Tr.phrase("Bộ mod tùy chỉnh của host\n")) + (card.info.fileCount || 0) + " file · " + ((card.info.sizeMiB || 0) === 0 ? "<0,1" : card.info.sizeMiB) + " MiB"
            color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.25
        }
        Text {
            width: parent.width; wrapMode: Text.WordWrap
            text: Tr.phrase("Chọn nội dung trước khi nhận. Pack đã đồng bộ sẽ cập nhật đúng bản chơi; pack mới tạo bản riêng.")
            color: Theme.textMuted; font.pixelSize: Theme.fontBody
        }
        ActionButton {
            objectName: "syncRoomPackButton"
            width: parent.width
            label: roomSyncBridge.busy ? Tr.phrase("Đang xử lý...") : Tr.phrase("Xem & chọn nội dung · Miễn phí")
            clickable: !roomSyncBridge.busy
            onClicked: roomSyncBridge.sync()
        }
        ActionButton {
            visible: roomSyncBridge.busy; primary: false; label: Tr.phrase("Huỷ đồng bộ")
            onClicked: roomSyncBridge.cancel()
        }
        Text {
            visible: Tr.message(roomSyncBridge.note) !== ""; width: parent.width; wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: Tr.message(roomSyncBridge.note); color: Theme.text; font.pixelSize: Theme.fontBody
        }
    }
}
