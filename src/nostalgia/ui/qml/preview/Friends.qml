import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "friendsPage"
    Component.onCompleted: socialBridge.setWatching(root.chatWatching)
    Component.onDestruction: socialBridge.setWatching(false)
    property string roomError: ""
    property int section: 0
    property bool invitesExpanded: true
    readonly property bool chatWatching: visible && section === 0 && friendPanel.chatExpanded
    onChatWatchingChanged: socialBridge.setWatching(root.chatWatching)
    readonly property bool compact: width < 860 * GlassTheme.scale
    Connections {
        target: multiplayerBridge
        function onFailed(message) { root.roomError = message; }
        function onStatusChanged() { root.roomError = ""; }
    }
    Connections { target: roomSyncBridge; function onFailed(message) { root.roomError = message; } }
    Connections { target: hostBridge; function onSetupRequested() { root.section = 1; } }
    InertialScroll {
        objectName: "friendsScroll"
        anchors.fill: parent
        contentHeight: contents.implicitHeight + 12
        Column {
            id: contents
            width: Math.min(parent.width - 10, 1220 * GlassTheme.scale)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14
            Item {
                width: parent.width
                visible: root.section === 1 || !root.compact || !socialBridge.peerId
                height: Math.max(title.implicitHeight, openRoom.height)
                PaymentText { id: title; width: parent.width - (openRoom.visible ? openRoom.width + 14 : 0); text: root.section === 1 ? Legacy.Tr.phrase("Chơi chung") : Legacy.Tr.phrase("Bạn bè"); font.pixelSize: GlassTheme.fontPage; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
                Button { id: openRoom; objectName: "friendsOpenRoom"; anchors.right: parent.right; visible: socialBridge.signedIn && !multiplayerBridge.active && !hostBridge.details.active; label: Legacy.Tr.phrase("Mở phòng"); primary: true; onClicked: hostBridge.openSetup() }
            }
            PaymentText { width: parent.width; visible: root.section === 1 || !root.compact || !socialBridge.peerId; text: socialBridge.signedIn ? socialBridge.friends.filter(function(friend) { return friend.online; }).length + Legacy.Tr.phrase(" bạn trực tuyến · Gặp nhau trong thế giới của bạn.") : Legacy.Tr.phrase("Kết nối tài khoản để lưu bạn bè và nhận lời mời."); color: GlassTheme.muted }
            MotionTabs { width: parent.width; labels: [Legacy.Tr.phrase("Bạn bè"), Legacy.Tr.phrase("Chơi chung")]; currentIndex: root.section; namePrefix: "friendsSection-"; onSelected: function(index) { root.section = index; } }
            GuideCard { width: parent.width; topicId: "friends"; visible: root.section === 0 && (!root.compact || !socialBridge.peerId) }
            ServiceAccountCard { width: parent.width; visible: !socialBridge.signedIn }
            PaymentText {
                objectName: "socialNote"
                width: parent.width
                visible: !!Legacy.Tr.message(socialBridge.note) || !!Legacy.Tr.message(root.roomError)
                text: [Legacy.Tr.message(socialBridge.note), Legacy.Tr.message(root.roomError)].filter(function(text) { return !!text; }).join("\n")
                color: GlassTheme.accent
            }
            Column {
                visible: socialBridge.signedIn
                width: parent.width; spacing: 14
                Column {
                    id: invitesArea
                    width: parent.width; spacing: 10
                    visible: root.section === 0 && (!root.compact || !socialBridge.peerId) && !multiplayerBridge.active && !hostBridge.details.active && socialBridge.invitations.length > 0
                    Button { objectName: "showInvitations"; width: parent.width; visible: root.compact; quiet: true; label: Legacy.Tr.phrase("Lời mời · ") + socialBridge.invitations.length + (root.invitesExpanded ? "  ↑" : "  ↓"); onClicked: root.invitesExpanded = !root.invitesExpanded }
                    InvitationList { width: parent.width; visible: !root.compact || root.invitesExpanded }
                }
                Button { objectName: "showActiveRoom"; width: parent.width; visible: root.section === 0 && (multiplayerBridge.active || hostBridge.details.active); label: roomSyncBridge.hostReady ? Legacy.Tr.phrase("Phòng sẵn sàng · Mở phòng để mời bạn") : Legacy.Tr.phrase("Đang mở phòng · Xem bước tiếp theo"); onClicked: root.section = 1 }
                RoomPanel { id: roomPanel; width: parent.width; visible: root.section === 1 && (multiplayerBridge.active || hostBridge.details.active) }
                Glass {
                    width: parent.width; visible: root.section === 1 && !multiplayerBridge.active && !hostBridge.details.active; padding: 24; height: playInfo.implicitHeight + 48
                    Column { id: playInfo; width: parent.width; spacing: 14
                        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Thế giới vui hơn khi có bạn."); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontDialog }
                        HostSteps { width: parent.width; currentStep: 0 }
                        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Tạo room, mời bạn và đồng bộ trước. Khi sẵn sàng, host khởi chạy Minecraft rồi bật LAN trong world."); color: GlassTheme.muted }
                        Button { label: Legacy.Tr.phrase("Mở phòng cùng bạn bè"); primary: true; onClicked: hostBridge.openSetup() }
                        GuideButton { topicId: "invite"; label: Legacy.Tr.phrase("Xem hướng dẫn có GIF") }
                        InvitationList { width: parent.width; visible: socialBridge.invitations.length > 0 }
                    }
                }
                Grid {
                    visible: root.section === 0
                    id: panels
                    width: parent.width
                    columns: root.compact ? 1 : 2
                    columnSpacing: 14; rowSpacing: 14
                    FriendsRail { width: root.compact ? panels.width : Math.min(300 * GlassTheme.scale, panels.width * 0.32); visible: !root.compact || !socialBridge.peerId }
                    FriendChat { id: friendPanel; width: root.compact ? panels.width : panels.width - Math.min(300 * GlassTheme.scale, panels.width * 0.32) - 14; compact: root.compact; availableHeight: Math.max(180 * GlassTheme.scale, root.height - panels.y - panels.parent.y - 12); visible: !root.compact || !!socialBridge.peerId }
                }
            }
        }
    }
}
