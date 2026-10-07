import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    objectName: "socialProfileDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(720 * GlassTheme.scale, parent ? parent.width - 40 : 720)
    height: Math.min(800 * GlassTheme.scale, parent ? parent.height - 40 : 800)
    x: parent ? (parent.width - width) / 2 : 0; y: parent ? (parent.height - height) / 2 : 0
    padding: 24; modal: true; dim: true; focus: true
    property bool editing: false
    readonly property var profile: profileBridge.details
    readonly property var details: profile.details || ({})
    readonly property bool mine: profile.mine === true
    function showFor(accountId) { if (profileBridge.busy) return; root.editing = false; root.open(); profileBridge.open(accountId); }
    onClosed: profileBridge.close()
    background: Glass { padding: 0; backdrop: Legacy.Theme.modalBackdrop; blurOpacity: 0.85; color: GlassTheme.alpha(GlassTheme.surface, 0.90) }
    Controls.Overlay.modal: Rectangle { color: "#aa080b12" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    contentItem: Item {
        Button { objectName: "closeSocialProfile"; z: 5; anchors.right: parent.right; width: 38; label: "×"; quiet: true; Accessible.name: "Đóng hồ sơ"; onClicked: root.close() }
        InertialScroll {
            objectName: "socialProfileScroll"
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: actions.top; anchors.bottomMargin: 18
            contentHeight: profileBody.implicitHeight + 8
            Column { id: profileBody; width: parent.width - 8; spacing: 18
                Item { width: parent.width; height: 146 * GlassTheme.scale
                    CosmeticBanner { objectName: "profileBanner"; anchors.fill: parent; decor: root.editing ? editor.previewDecor : root.details.decor || "none" }
                    SocialAvatar { objectName: "profileAvatar"; x: 18; anchors.verticalCenter: parent.verticalCenter; size: 98 * GlassTheme.scale; playerName: root.profile.name || ""; source: root.profile.avatar_url || ""; decor: root.editing ? editor.previewDecor : root.details.decor || "none"; online: root.profile.online === true }
                    Column { x: 132 * GlassTheme.scale; anchors.verticalCenter: parent.verticalCenter; width: parent.width - x - 24; spacing: 7
                        PaymentText { width: parent.width; text: root.profile.name || "Hồ sơ người chơi"; font.pixelSize: GlassTheme.fontDialog; font.family: GlassTheme.displayFont; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: root.profile.online ? "Trực tuyến · Sẵn sàng chơi cùng" : "Ngoại tuyến"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                        ProfileBadge { visible: !!root.profile.badge; badge: root.profile.badge || "" }
                    }
                }
                PaymentText { width: parent.width; visible: !!profileBridge.note; text: profileBridge.note; color: GlassTheme.muted }
                Column { width: parent.width; spacing: 10; visible: !!root.profile.account_id && !root.editing
                    PaymentText { width: parent.width; text: root.details.bio || "Người chơi chưa thêm giới thiệu."; color: GlassTheme.muted }
                    SocialProfileShowcase { width: parent.width; profile: root.profile; details: root.details }
                }
                SocialProfileEditor { id: editor; width: parent.width; visible: root.editing; profile: root.profile; details: root.details }
            }
        }
        Flow { id: actions; anchors.bottom: parent.bottom; width: parent.width; spacing: 10
            Button { objectName: "editSocialProfile"; visible: root.mine && !root.editing; label: "Chỉnh sửa hồ sơ"; primary: true; clickable: !profileBridge.busy; onClicked: { editor.populate(); root.editing = true; } }
            Button { objectName: "saveSocialProfile"; visible: root.editing; label: "Lưu hồ sơ"; primary: true; clickable: !profileBridge.busy; onClicked: editor.save() }
            Button { objectName: "cancelSocialProfileEdit"; visible: root.editing; label: "Huỷ"; quiet: true; clickable: !profileBridge.busy; onClicked: root.editing = false }
            Button { visible: !root.mine && !!root.profile.account_id; label: "Nhắn tin"; primary: true; onClicked: { socialBridge.selectFriend(root.profile.account_id); root.close(); } }
        }
    }
    Connections { target: profileBridge; function onSaved() { root.editing = false; } function onCleared() { if (root.opened) root.close(); } }
    Connections { target: socialBridge; function onChanged() { if (root.opened && !socialBridge.signedIn) root.close(); } }
}
