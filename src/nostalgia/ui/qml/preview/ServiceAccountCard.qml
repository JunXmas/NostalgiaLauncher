import QtQuick

Glass {
    id: root
    implicitHeight: contents.implicitHeight + 36
    height: implicitHeight
    padding: 18
    Column {
        id: contents
        width: parent.width
        spacing: 12
        Grid {
            id: grid
            width: parent.width
            columns: socialBridge.signedIn && width >= 620 * GlassTheme.scale ? 2 : 1
            columnSpacing: 18
            rowSpacing: 12
            Column {
                width: grid.columns === 2 ? grid.width - controls.width - 18 : grid.width
                spacing: 8
                PaymentText {
                    width: parent.width
                    text: socialBridge.signedIn ? socialBridge.account.name : "Cùng bạn bè, ở mọi nơi."
                    font.pixelSize: GlassTheme.fontTitle
                    font.weight: Font.DemiBold
                }
                PaymentText {
                    width: parent.width
                    color: GlassTheme.muted
                    text: socialBridge.signedIn ? (socialBridge.account.plus ? "Nostalgia " + socialBridge.account.planName + (socialBridge.account.badge ? " · " + socialBridge.account.badge : "") : "Miễn phí") + " · Tài khoản Google"
                        : "Dùng Google để lưu bạn bè và nhận lời mời trên các máy của bạn. Tài khoản Minecraft vẫn dùng riêng để chơi game."
                }
            }
            Flow {
                id: controls
                width: grid.columns === 2 ? 290 * GlassTheme.scale : grid.width
                spacing: 8
                Button {
                    objectName: "socialGoogleLogin"
                    provider: "google"
                    visible: !socialBridge.signedIn && !socialBridge.signingIn
                    label: "Tiếp tục với Google  ↗"
                    primary: true
                    clickable: socialBridge.configured && !socialBridge.busy
                    onClicked: socialBridge.signIn()
                }
                Button { visible: socialBridge.signingIn; label: "Mở lại Google  ↗"; onClicked: socialBridge.openGoogle() }
                Button { visible: socialBridge.signingIn; label: "Huỷ"; quiet: true; onClicked: socialBridge.cancelSignIn() }

            }
        }
        PaymentText {
            objectName: "socialAccountHint"
            width: parent.width
            text: socialBridge.signedIn ? "Mã kết bạn · " + socialBridge.account.friendCode + "  ·  Đăng nhập máy mới sẽ đăng xuất máy này."
                : socialBridge.configured ? "Hoàn tất đăng nhập trong trình duyệt. Launcher tự kết nối, không cần nhập mã."
                : "Đăng nhập Google chưa khả dụng trong bản thử này. Chờ bản cập nhật từ Nostalgia."
            color: GlassTheme.muted
            font.pixelSize: GlassTheme.fontNote
        }
    }
}
