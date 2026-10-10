import QtQuick
import "../" as Legacy

Column {
    id: root
    spacing: 10
    readonly property bool needsSync: !!roomSyncBridge.offer.name && !roomSyncBridge.guestInstanceId
    readonly property bool waitingPack: multiplayerBridge.shareState === "pending" && !roomSyncBridge.offer.name
    PaymentText {
        width: parent.width
        text: multiplayerBridge.connectionKind === "direct" ? Legacy.Tr.phrase("● Kết nối trực tiếp · DTLS")
            : multiplayerBridge.connectionKind === "connecting" ? Legacy.Tr.phrase("Đang tìm đường kết nối trực tiếp…")
            : Legacy.Tr.phrase("Kết nối qua relay · TLS")
        color: multiplayerBridge.connectionKind === "direct" ? GlassTheme.brand : GlassTheme.muted
        font.pixelSize: GlassTheme.fontCaption
    }
    Select {
        id: pack; objectName: "guestRoomPack"; width: parent.width
        visible: !roomSyncBridge.offer.name
        model: bridge.instances.map(function(instance) { return instance.label; })
    }
    PaymentText {
        width: parent.width; visible: root.needsSync
        text: Legacy.Tr.phrase("Xem và chọn nội dung modpack bên dưới trước khi khởi chạy. Mod custom có thể chạy mã trên máy bạn.")
        color: GlassTheme.muted
    }
    Button {
        objectName: "launchGuestRoom"
        label: root.waitingPack ? Legacy.Tr.phrase("Đang kiểm tra modpack của phòng...") : !multiplayerBridge.worldReady ? Legacy.Tr.phrase("Đang chờ host mở world") : Legacy.Tr.phrase("Khởi chạy & vào world")
        primary: true
        clickable: multiplayerBridge.connectionKind !== "connecting" && !root.waitingPack && multiplayerBridge.worldReady && !root.needsSync && !bridge.busy && !bridge.gameRunning && !bridge.storageBusy && !roomSyncBridge.busy && (!!roomSyncBridge.guestInstanceId || !!bridge.instances[pack.currentIndex])
        onClicked: roomSyncBridge.launchGuest((bridge.instances[pack.currentIndex] || {}).instanceId || "")
    }
}
