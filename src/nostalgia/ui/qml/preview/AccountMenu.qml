import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy
Controls.Popup {
    id: root
    objectName: "accountMenu"
    property Item anchorItem: null
    signal navigate(int index)
    parent: Controls.Overlay.overlay
    width: Math.min(300 * GlassTheme.scale, parent ? parent.width - 24 : 300)
    height: menu.implicitHeight + 24; padding: 12
    x: anchorItem && parent ? Math.max(12, anchorItem.mapToItem(parent, 0, 0).x) : 12
    y: anchorItem && parent ? Math.max(12, anchorItem.mapToItem(parent, 0, 0).y - height - 10) : 12
    closePolicy: Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutside
    background: PopupGlass {}
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.quick } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
    contentItem: Column {
        id: menu; spacing: 6
        PaymentText { width: parent.width; text: socialBridge.signedIn ? socialBridge.account.name : bridge.activePlayerName || "Khách"; font.weight: Font.DemiBold }
        PaymentText { width: parent.width; text: socialBridge.signedIn ? "Nostalgia · " + (socialBridge.account.plus ? socialBridge.account.planName : "Miễn phí") : "Tài khoản Minecraft"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        Rectangle { width: parent.width; height: 1; color: GlassTheme.stroke }
        Button { objectName: "openMyProfile"; width: parent.width; visible: socialBridge.signedIn; label: "Hồ sơ của tôi"; quiet: true; onClicked: { root.close(); socialProfileDialog.showFor(socialBridge.account.accountId); } }
        Button { objectName: "openCosmeticLibrary"; width: parent.width; label: "Thư viện cosmetic"; quiet: true; onClicked: { root.close(); root.navigate(7); } }
        Button { width: parent.width; label: "Tài khoản Minecraft"; quiet: true; onClicked: { root.close(); root.navigate(3); } }
        Button { objectName: "copyFriendCode"; width: parent.width; visible: socialBridge.signedIn; label: "Chép mã kết bạn"; quiet: true; onClicked: socialBridge.copyFriendCode() }
        Rectangle { width: parent.width; height: 1; visible: socialBridge.signedIn; color: GlassTheme.stroke }
        Button { objectName: "socialLogout"; width: parent.width; visible: socialBridge.signedIn; label: "Đăng xuất Nostalgia"; quiet: true; danger: true; clickable: !socialBridge.busy; onClicked: { root.close(); confirmDialog.ask("Đăng xuất Nostalgia?", "Phòng chơi chung sẽ đóng. Tài khoản Minecraft, bản chơi và thế giới trên máy vẫn được giữ lại.", function() { socialBridge.signOut(); }); } }
    }
}
