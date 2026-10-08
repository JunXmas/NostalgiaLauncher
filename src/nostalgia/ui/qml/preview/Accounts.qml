import QtQuick
import "../" as Legacy
Item {
    id: page; objectName: "accountsPage"
    property string shownId: bridge.activeAccountId
    property var shown: ({})
    readonly property bool hasShown: !!shown && !!shown.playerName
    function refreshShown() { page.shown = accountBridge.accountWithId(page.shownId); }
    Component.onCompleted: refreshShown()
    onShownIdChanged: refreshShown()
    Connections { target: bridge; function onActiveAccountChanged() { page.shownId = bridge.activeAccountId; } }
    Connections { target: accountBridge; function onSkinsChanged() { page.refreshShown(); } }
    Column { id: header; width: parent.width; spacing: 8
        PaymentText { width: parent.width - add.width - 16; text: "Tài khoản & skin"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontPage; font.weight: Font.DemiBold }
        PaymentText { width: parent.width; text: "Nhân vật của bạn. Thay skin ngay tại đây."; color: GlassTheme.muted }
    }
    Button { id: add; objectName: "addAccountButton"; anchors.right: parent.right; label: "Thêm tài khoản  +"; primary: true; onClicked: addDialog.openDialog() }
    InertialScroll {
        id: accountScroll; objectName: "accountsScroll"
        anchors.top: header.bottom; anchors.topMargin: 24; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        contentHeight: contents.implicitHeight + 12
        Column { id: contents; width: Math.min(parent.width - 10, 1320 * GlassTheme.scale); anchors.horizontalCenter: parent.horizontalCenter; spacing: 20
            Flow { width: parent.width; spacing: 10
                Repeater { model: accountBridge.accounts
                    Glass { width: Math.min(300 * GlassTheme.scale, contents.width); height: 104 * GlassTheme.scale; padding: 16
                        Button { anchors.right: parent.right; width: 28; height: 28; label: "×"; danger: true; quiet: true; Accessible.name: "Gỡ tài khoản " + modelData.playerName; onClicked: { var accountId = modelData.accountId; confirmDialog.ask("Gỡ tài khoản Minecraft?", "Skin trong thư viện và các bản chơi được giữ lại.", function() { bridge.removeAccount(accountId); }); } }
                        Legacy.SkinFace { x: 0; anchors.verticalCenter: parent.verticalCenter; size: 44; source: modelData.skinFile || "" }
                        Column { x: 58; width: parent.width - x - 24; spacing: 8
                            PaymentText { width: parent.width; text: modelData.playerName; font.weight: Font.DemiBold; elide: Text.ElideRight; maximumLineCount: 1 }
                            Row { spacing: 6; ProviderLogo { width: 16; height: 16; provider: modelData.accountKind; visible: modelData.accountKind === "microsoft" } PaymentText { text: modelData.kindLabel; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption } }
                            Button { height: 28; label: page.shownId === modelData.accountId ? "Đang chọn ✓" : "Chọn tài khoản"; selected: page.shownId === modelData.accountId; quiet: true; onClicked: { page.shownId = modelData.accountId; bridge.setActiveAccount(modelData.accountId); } }
                        }
                    }
                }
            }
            Grid {
                width: parent.width; columns: width > 860 * GlassTheme.scale ? 2 : 1; columnSpacing: 20; rowSpacing: 20
                Glass {
                    width: parent.columns === 2 ? 300 * GlassTheme.scale : parent.width; height: 430 * GlassTheme.scale; padding: 24
                    PaymentText { width: parent.width; text: page.hasShown ? page.shown.playerName : "Nhân vật của bạn"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontTitle }
                    Legacy.SkinFigure { objectName: "accountSkinFigure"; anchors.centerIn: parent; width: 150 * GlassTheme.scale; height: width * 2; source: page.hasShown ? page.shown.skinFile || "" : ""; slim: page.hasShown && page.shown.slim === true; revision: page.hasShown ? page.shown.skinDigest || "" : ""; visible: page.hasShown }
                    PaymentText { anchors.bottom: parent.bottom; width: parent.width; text: page.hasShown ? "Kéo để xoay · ← →
" + (page.shown.slim ? "Alex · Slim" : "Steve · Wide") : "Thêm tài khoản để xem nhân vật và sử dụng skin."; color: GlassTheme.muted; horizontalAlignment: Text.AlignHCenter }
                }
                Legacy.SkinPanel { objectName: "skinPanel"; width: parent.columns === 2 ? parent.width - 300 * GlassTheme.scale - 20 : parent.width; height: 520 * GlassTheme.scale; shown: page.shown; hasShown: page.hasShown }
            }
        }
    }
    Legacy.AddAccountDialog {
        id: addDialog; objectName: "addAccountDialog"
        parent: page.Window.window ? page.Window.window.contentItem : page
        anchors.fill: parent
    }
}
