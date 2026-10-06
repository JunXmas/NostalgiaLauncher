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
                    font.pixelSize: 22 * GlassTheme.scale
                    font.weight: Font.DemiBold
                }
                PaymentText {
                    width: parent.width
                    color: GlassTheme.muted
                    text: socialBridge.signedIn ? (socialBridge.account.plus ? "Nostalgia Plus" + (socialBridge.account.badge ? " · " + socialBridge.account.badge : "") : "Miễn phí") + " · Tài khoản Google"
                        : "Dùng Google để lưu bạn bè, nhận lời mời và mang Plus sang máy mới. Tài khoản Minecraft vẫn dùng riêng để chơi game."
                }
            }
            Flow {
                id: controls
                width: grid.columns === 2 ? 290 * GlassTheme.scale : grid.width
                spacing: 8
                Button {
                    objectName: "socialGoogleLogin"
                    visible: !socialBridge.signedIn && !socialBridge.signingIn
                    label: "Tiếp tục với Google  ↗"
                    primary: true
                    clickable: socialBridge.configured && !socialBridge.busy
                    onClicked: socialBridge.signIn()
                }
                Button { visible: socialBridge.signingIn; label: "Mở lại Google  ↗"; onClicked: socialBridge.openGoogle() }
                Button { visible: socialBridge.signingIn; label: "Huỷ"; quiet: true; onClicked: socialBridge.cancelSignIn() }
                Button { objectName: "copyFriendCode"; visible: socialBridge.signedIn; label: "Chép mã kết bạn"; onClicked: socialBridge.copyFriendCode() }
                Button {
                    objectName: "socialLogout"
                    visible: socialBridge.signedIn
                    label: "Đăng xuất"; quiet: true; clickable: !socialBridge.busy
                    onClicked: confirmDialog.ask("Đăng xuất Google?", "Phòng chơi chung sẽ đóng. Bản chơi và thế giới trên máy vẫn được giữ lại.", function() { socialBridge.signOut(); })
                }
            }
        }
        PaymentText {
            objectName: "socialAccountHint"
            width: parent.width
            text: socialBridge.signedIn ? "Mã kết bạn · " + socialBridge.account.friendCode + "  ·  Đăng nhập máy mới sẽ đăng xuất máy này."
                : socialBridge.configured ? "Bạn bè, chat và chơi chung miễn phí. Chỉ chủ phòng cần Plus để đồng bộ modpack."
                : "PREVIEW · Đăng nhập Google sẽ mở khi dịch vụ được cấu hình."
            color: GlassTheme.muted
            font.pixelSize: 11 * GlassTheme.scale
        }
    }
}
