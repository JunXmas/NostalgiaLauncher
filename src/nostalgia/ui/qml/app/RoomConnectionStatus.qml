import QtQuick
import "../" as Legacy

Column {
    id: root
    objectName: "roomConnectionStatus"
    width: parent.width
    spacing: 10
    readonly property var stages: [
        {key: "room", title: Legacy.Tr.phrase("Phòng chơi"), state: multiplayerBridge.roomVerified ? Legacy.Tr.phrase("Đã vào phòng") : multiplayerBridge.connectionKind === "failed" ? Legacy.Tr.phrase("Chưa xác nhận được phòng") : Legacy.Tr.phrase("Đang kiểm tra phòng…"), ready: multiplayerBridge.roomVerified, failed: !multiplayerBridge.roomVerified && multiplayerBridge.connectionKind === "failed"},
        {key: "peer", title: Legacy.Tr.phrase("Kết nối hai máy"),
         state: multiplayerBridge.connectionKind === "direct" ? Legacy.Tr.phrase("Đã kết nối · Có mã hóa")
             : multiplayerBridge.connectionKind === "failed" ? Legacy.Tr.phrase("Chưa kết nối được")
             : multiplayerBridge.connectionKind === "connecting" ? Legacy.Tr.phrase("Đang kết nối…")
             : Legacy.Tr.phrase("Chờ host mở world để kết nối"),
         ready: multiplayerBridge.connectionKind === "direct", failed: multiplayerBridge.connectionKind === "failed"},
        {key: "world", title: "World",
         state: multiplayerBridge.locked ? Legacy.Tr.phrase("Host đang khóa phòng")
             : multiplayerBridge.worldAvailable ? Legacy.Tr.phrase("World đã mở") : Legacy.Tr.phrase("Chờ host bật LAN"),
         ready: multiplayerBridge.worldAvailable && !multiplayerBridge.locked, failed: false}
    ]
    Repeater {
        model: root.stages
        Row {
            required property var modelData
            width: root.width; spacing: 10
            Rectangle {
                width: 8; height: 8; radius: 4; y: 6 * GlassTheme.scale
                color: modelData.failed ? GlassTheme.danger : modelData.ready ? GlassTheme.brand : GlassTheme.muted
            }
            PaymentText {
                objectName: "roomStage-" + modelData.key
                width: parent.width - 18
                text: modelData.title + " · " + modelData.state
                color: modelData.failed ? GlassTheme.danger : GlassTheme.text
                font.pixelSize: GlassTheme.fontBody
            }
        }
    }
    PaymentText {
        objectName: "roomConnectionNote"
        width: parent.width
        visible: !!multiplayerBridge.connectionNote
        text: Legacy.Tr.message(multiplayerBridge.connectionNote)
        color: multiplayerBridge.connectionKind === "failed" ? GlassTheme.danger : GlassTheme.muted
    }
    Button {
        objectName: "retryRoomConnection"
        visible: multiplayerBridge.canRetryConnection
        label: Legacy.Tr.phrase("Thử kết nối lại")
        primary: true
        onClicked: multiplayerBridge.retryConnection()
    }
}
