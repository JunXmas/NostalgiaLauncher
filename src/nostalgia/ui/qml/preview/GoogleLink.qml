import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "googleLinkStep"
    readonly property bool compact: width < 1100 * GlassTheme.scale
    onVisibleChanged: {
        if (visible) {
            entrance.restart();
            if (socialBridge.configured) connectButton.forceActiveFocus();
            else laterButton.forceActiveFocus();
        } else entrance.stop();
    }
    Row {
        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: root.compact ? 24 : 48
        spacing: 12
        Image { width: 32; height: 32; source: "../assets/logo.png"; mipmap: true }
        PaymentText { anchors.verticalCenter: parent.verticalCenter; text: "Nostalgia"; font.pixelSize: GlassTheme.fontBrand; font.weight: Font.DemiBold }
    }
    Column {
        visible: !root.compact
        x: 64; y: Math.max(160, (root.height - height) * 0.46)
        width: Math.max(240, root.width - card.width - 180); spacing: 22
        PaymentText { text: "TÀI KHOẢN NOSTALGIA"; color: GlassTheme.accent; font.pixelSize: GlassTheme.fontNote; font.letterSpacing: 2 }
        PaymentText { width: parent.width; text: "Thế giới của bạn.\nBạn bè của bạn."; font.family: GlassTheme.displayFont; font.pixelSize: 56; font.weight: Font.DemiBold; lineHeight: 1.1 }
        PaymentText { width: Math.min(360, parent.width); text: "Giữ kết nối và mang hồ sơ của bạn sang máy mới."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontAction; lineHeight: 1.5 }
    }
    Glass {
        id: card
        objectName: "googleLinkCard"
        x: root.compact ? (root.width - width) / 2 : root.width - width - 64
        y: (root.height - height) / 2
        width: Math.min(500 * GlassTheme.scale, root.width - 48)
        height: Math.min(form.implicitHeight + actions.implicitHeight + 82 * GlassTheme.scale, root.height - (root.compact ? 120 : 156))
        padding: 32 * GlassTheme.scale
        backdrop: Legacy.Theme.modalBackdrop; blurOpacity: 0.9; finishOpacity: 0.65
        color: GlassTheme.alpha(GlassTheme.surface, 0.74)
        transform: Translate { id: cardOffset }
        Item {
            anchors.fill: parent
            InertialScroll {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                anchors.bottom: actions.top; anchors.bottomMargin: 18 * GlassTheme.scale
                contentHeight: form.implicitHeight
                Column {
                    id: form; width: parent.width; spacing: (root.compact ? 12 : 20) * GlassTheme.scale
                    Row {
                        width: parent.width; spacing: 8
                        PaymentText { text: "✓"; color: GlassTheme.accent }
                        PaymentText { width: parent.width - 24; text: bridge.activePlayerName + " · " + googleLinkBridge.provider + " đã đăng nhập"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontLabel }
                    }
                    Column {
                        width: parent.width; spacing: 10 * GlassTheme.scale
                        PaymentText { width: parent.width; text: root.compact ? "Liên kết Google với Nostalgia" : "Liên kết Google\nvới Nostalgia"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontLogin; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; visible: !root.compact || !socialBridge.signingIn; text: root.compact ? "Google đồng bộ bạn bè, hồ sơ và Plus đã mua." : "Minecraft đã sẵn sàng. Thêm tài khoản Google để sử dụng và đồng bộ các dịch vụ Nostalgia."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontBody; lineHeight: 1.4 }
                    }
                    Column {
                        visible: !root.compact; width: parent.width; spacing: 12 * GlassTheme.scale
                        PaymentText { width: parent.width; text: "Bạn bè & lời mời chơi chung"; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: "Hồ sơ & quyền lợi Plus đã mua trên các máy"; font.weight: Font.DemiBold }
                    }
                }
            }
            Column {
                id: actions; objectName: "googleLinkActions"
                anchors.bottom: parent.bottom; width: parent.width; spacing: 12 * GlassTheme.scale
                Rectangle { width: parent.width; height: 1; color: GlassTheme.stroke }
                Button {
                    id: connectButton; objectName: "googleLinkConnect"
                    width: parent.width; height: 48 * GlassTheme.scale
                    provider: "google"; primary: true
                    label: socialBridge.signingIn ? "Đang chờ Google…" : socialBridge.busy ? "Đang kết nối…" : "Liên kết với Google  ↗"
                    clickable: socialBridge.configured && !socialBridge.busy && !socialBridge.signingIn
                    onClicked: socialBridge.signIn()
                }
                PaymentText {
                    objectName: "googleLinkStatus"; width: parent.width
                    text: socialBridge.note || (socialBridge.configured ? "Xác thực qua trình duyệt. Launcher tự kết nối khi hoàn tất." : "Google chưa khả dụng trong bản thử này. Bạn có thể để sau và tiếp tục chơi Minecraft.")
                    color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote
                    maximumLineCount: 3; elide: Text.ElideRight
                }
                Row {
                    width: parent.width; spacing: 8 * GlassTheme.scale
                    Button { objectName: "googleLinkReopen"; visible: socialBridge.signingIn; width: (parent.width - parent.spacing) / 2; height: 42 * GlassTheme.scale; label: "Mở lại Google  ↗"; quiet: true; onClicked: socialBridge.openGoogle() }
                    Button { id: laterButton; objectName: "googleLinkLater"; width: socialBridge.signingIn ? (parent.width - parent.spacing) / 2 : parent.width; height: 42 * GlassTheme.scale; label: socialBridge.signingIn ? "Để sau" : "Để sau · Vào launcher"; quiet: true; onClicked: googleLinkBridge.defer() }
                }
                PaymentText { width: parent.width; visible: !root.compact; text: "Bạn vẫn chơi Minecraft bình thường. Có thể liên kết Google sau tại mục Bạn bè."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote; horizontalAlignment: Text.AlignHCenter }
            }
        }
    }
    ParallelAnimation {
        id: entrance
        NumberAnimation { target: card; property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
        NumberAnimation { target: cardOffset; property: "y"; from: GlassTheme.reducedMotion ? 0 : 12; to: 0; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
    }
    Connections {
        target: GlassTheme
        function onReducedMotionChanged() { if (GlassTheme.reducedMotion) entrance.complete(); }
    }
}
