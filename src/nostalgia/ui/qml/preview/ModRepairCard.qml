import QtQuick
import "../" as Legacy

Item {
    id: root
    required property var modelData
    readonly property var proposal: modelData
    signal replaceRequested(string groupId)
    objectName: "repairCard-" + proposal.groupId
    height: presentation.implicitHeight + 36
    Image {
        id: artwork
        anchors.fill: parent
        source: root.proposal.icon
        sourceSize: Qt.size(160,160)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        visible: false
    }
    Glass {
        anchors.fill: parent
        padding: 18; radius: 18
        backdrop: artwork
        blurOpacity: 0.18; blurRadius: 48
        color: GlassTheme.alpha(GlassTheme.surface, 0.86)
        Column {
            id: presentation
            width: parent.width; spacing: 12
            Row {
                width: parent.width; spacing: 12
                Legacy.ProjectIcon { source: root.proposal.icon; fallbackText: root.proposal.name; width: 46; height: 46 }
                Column {
                    width: parent.width - 58; spacing: 4
                    PaymentText { width: parent.width; text: root.proposal.name; font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold; textFormat: Text.PlainText }
                    PaymentText { width: parent.width; text: root.proposal.currentVersion + "  →  " + root.proposal.version; color: GlassTheme.accent; textFormat: Text.PlainText }
                }
            }
            PaymentText { width: parent.width; text: "Minecraft " + root.proposal.minecraft + " · " + root.proposal.loader; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote; textFormat: Text.PlainText }
            PaymentText { width: parent.width; text: root.proposal.reason; textFormat: Text.PlainText }
            PaymentText { width: parent.width; text: root.proposal.downloads > 1 ? "Bao gồm " + root.proposal.downloads + " mod và phụ thuộc. Tải, kiểm hash, sao lưu trước khi thay." : "Kiểm hash và lưu bản trước để hoàn tác. Giữ nguyên worlds."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            Button {
                objectName: "replaceMod-" + root.proposal.groupId
                label: root.proposal.isReplacement ? "Replace  ↓" : "Tắt bản trùng/xung đột"
                primary: true
                clickable: root.proposal.canReplace && !modRepairBridge.busy && !bridge.gameRunning && !bridge.busy && !bridge.storageBusy
                onClicked: root.replaceRequested(root.proposal.groupId)
            }
            PaymentText { width: parent.width; visible: !root.proposal.canReplace; text: "Còn phụ thuộc chưa xác minh; xem lý do bên dưới trước khi sửa."; color: GlassTheme.danger; font.pixelSize: GlassTheme.fontNote }
        }
    }
}
