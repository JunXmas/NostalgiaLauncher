import QtQuick
import "../" as Legacy
import "CosmeticCatalog.js" as Cosmetics
Item {
    id: root; objectName: "cosmeticLibrary"
    property string previewDecor: "none"
    readonly property bool canEquip: socialBridge.signedIn && socialBridge.account.cosmeticPlus === true
    readonly property var ownedCosmetics: cosmeticBridge.details.ownedCosmetics || []
    function load() { if (socialBridge.signedIn) cosmeticBridge.refresh(); }
    Component.onCompleted: root.load()
    Connections { target: socialBridge; function onSessionChanged() { root.previewDecor = "none"; root.load(); } }
    Connections { target: cosmeticBridge; function onChanged() { if (cosmeticBridge.details.loaded) root.previewDecor = cosmeticBridge.details.decor; } }
    InertialScroll {
        anchors.fill: parent; contentHeight: body.implicitHeight + 20
        Column {
            id: body; width: Math.min(parent.width - 10, 1140 * GlassTheme.scale); anchors.horizontalCenter: parent.horizontalCenter; spacing: 24
            Column { width: parent.width; spacing: 8
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Thư viện cosmetic"); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontPage; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Một diện mạo riêng cho những cuộc gặp gỡ."); color: GlassTheme.muted }
            }
            GuideCard { width: parent.width; topicId: "cosmetic" }
            Item {
                width: parent.width; height: (width < 650 * GlassTheme.scale ? 290 : 210) * GlassTheme.scale
                CosmeticBanner { anchors.fill: parent; decor: root.previewDecor }
                SocialAvatar { y: parent.width < 650 * GlassTheme.scale ? 24 : (parent.height - height) / 2; x: 28; size: (parent.width < 650 * GlassTheme.scale ? 72 : 120) * GlassTheme.scale; source: cosmeticBridge.details.avatarUrl || socialBridge.account.avatarUrl || ""; playerName: socialBridge.account.name || bridge.activePlayerName || Legacy.Tr.phrase("Bạn"); decor: root.previewDecor; showPresence: false }
                Column { x: parent.width < 650 * GlassTheme.scale ? 28 : 174 * GlassTheme.scale; y: parent.width < 650 * GlassTheme.scale ? 115 * GlassTheme.scale : (parent.height - height) / 2; width: parent.width - x - 28; spacing: 10
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase(Cosmetics.name(root.previewDecor, cosmeticBridge.sets)); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontPage; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: root.previewDecor !== "none" && !Cosmetics.find(root.previewDecor, cosmeticBridge.sets) ? Legacy.Tr.phrase("Cập nhật launcher để hiển thị bộ cosmetic đang dùng.") : root.previewDecor === cosmeticBridge.details.decor ? Legacy.Tr.phrase("Diện mạo đang dùng trên hồ sơ của bạn") : Legacy.Tr.phrase("Xem thử · Hồ sơ chưa thay đổi"); color: GlassTheme.muted }
                    Button { objectName: "cosmeticEquip"; label: root.previewDecor === cosmeticBridge.details.decor ? Legacy.Tr.phrase("Đang sử dụng ✓") : Legacy.Tr.phrase("Sử dụng diện mạo"); primary: true; clickable: (root.canEquip || socialBridge.signedIn && (root.previewDecor === "none" || root.ownedCosmetics.indexOf(root.previewDecor) >= 0)) && cosmeticBridge.details.loaded && !cosmeticBridge.busy && root.previewDecor !== cosmeticBridge.details.decor; onClicked: cosmeticBridge.equip(root.previewDecor) }
                }
            }
            CosmeticPicker { width: parent.width; selectedDecor: cosmeticBridge.details.decor || "none"; previewDecor: root.previewDecor; avatarSource: cosmeticBridge.details.avatarUrl || socialBridge.account.avatarUrl || ""; playerName: socialBridge.account.name || bridge.activePlayerName || Legacy.Tr.phrase("Bạn"); canEquip: root.canEquip; ownedCosmetics: root.ownedCosmetics; onChosen: function(decor) { root.previewDecor = decor; } }
            ServiceAccountCard { width: parent.width; visible: !socialBridge.signedIn }
            ProfilePerks { width: parent.width }
            PaymentText { width: parent.width; visible: cosmeticBridge.busy; text: Legacy.Tr.message(cosmeticBridge.activity); color: GlassTheme.accent }
            PaymentText { id: failure; property string sourceMessage: ""; width: parent.width; text: Legacy.Tr.message(sourceMessage); visible: !!text; color: GlassTheme.danger; Connections { target: cosmeticBridge; function onFailed(message) { failure.sourceMessage = message; } } }
        }
    }
}
