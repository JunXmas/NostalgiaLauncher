import QtQuick
import "../" as Legacy
import "ActionReasons.js" as Reasons

Column {
    id: root
    spacing: 10
    readonly property bool needsSync: !!roomSyncBridge.offer.name && !roomSyncBridge.guestInstanceId
    readonly property bool waitingPack: multiplayerBridge.shareState === "pending" && !roomSyncBridge.offer.name
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
        id: launch
        objectName: "launchGuestRoom"
        label: Legacy.Tr.phrase("Khởi chạy & vào world")
        primary: true
        disabledReason: Legacy.Tr.phrase(Reasons.joining(bridge, multiplayerBridge, roomSyncBridge, roomSyncBridge.guestInstanceId || (bridge.instances[pack.currentIndex] || {}).instanceId || "", root.waitingPack, root.needsSync))
        clickable: !disabledReason
        onClicked: roomSyncBridge.launchGuest((bridge.instances[pack.currentIndex] || {}).instanceId || "")
    }
    ActionHint { objectName: "guestLaunchHint"; width: parent.width; reason: launch.disabledReason }
}
