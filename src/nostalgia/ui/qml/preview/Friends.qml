import QtQuick

Item {
    id: root
    objectName: "friendsPage"
    Component.onCompleted: socialBridge.setWatching(true)
    Component.onDestruction: socialBridge.setWatching(false)
    property string roomError: ""
    property bool accountExpanded: false
    property bool invitesExpanded: false
    readonly property bool compact: width < 860 * GlassTheme.scale
    Connections {
        target: multiplayerBridge
        function onFailed(message) { root.roomError = message; }
        function onStatusChanged() { root.roomError = ""; }
    }
    Connections { target: roomSyncBridge; function onFailed(message) { root.roomError = message; } }
    InertialScroll {
        objectName: "friendsScroll"
        anchors.fill: parent
        contentHeight: contents.implicitHeight + 12
        Column {
            id: contents
            width: parent.width - 10
            spacing: 14
            Item {
                width: parent.width
                visible: !root.compact || !socialBridge.peerId
                height: Math.max(title.implicitHeight, openRoom.height)
                PaymentText { id: title; width: parent.width - (openRoom.visible ? openRoom.width + 14 : 0); text: "Bạn bè"; font.pixelSize: GlassTheme.fontPage; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
                Button { id: openRoom; objectName: "friendsOpenRoom"; anchors.right: parent.right; visible: socialBridge.signedIn && !multiplayerBridge.active; label: "Mở phòng"; primary: true; onClicked: multiplayerBridge.startHosting() }
            }
            Item {
                width: parent.width
                height: accountLink.height
                visible: socialBridge.signedIn && (!root.compact || !socialBridge.peerId)
                PaymentText { width: parent.width - accountLink.width - 12; anchors.verticalCenter: parent.verticalCenter; text: socialBridge.friends.filter(function(friend) { return friend.online; }).length + " bạn đang trực tuyến"; color: GlassTheme.muted }
                Button { id: accountLink; objectName: "socialAccountToggle"; anchors.right: parent.right; quiet: true; label: root.accountExpanded ? "Thu gọn tài khoản  ↑" : "Tài khoản Google  ↓"; onClicked: root.accountExpanded = !root.accountExpanded }
            }
            ServiceAccountCard { width: parent.width; visible: !socialBridge.signedIn || root.accountExpanded }
            PaymentText {
                objectName: "socialNote"
                width: parent.width
                visible: !!socialBridge.note || !!root.roomError
                text: [socialBridge.note, root.roomError].filter(function(text) { return !!text; }).join("\n")
                color: GlassTheme.accent
            }
            Column {
                visible: socialBridge.signedIn
                width: parent.width; spacing: 14
                Column {
                    id: invitesArea
                    width: parent.width; spacing: 10
                    visible: !multiplayerBridge.active && socialBridge.invitations.length > 0
                    Button { objectName: "showInvitations"; width: parent.width; visible: root.compact; quiet: true; label: "Lời mời · " + socialBridge.invitations.length + (root.invitesExpanded ? "  ↑" : "  ↓"); onClicked: root.invitesExpanded = !root.invitesExpanded }
                    InvitationList { width: parent.width; visible: !root.compact || root.invitesExpanded }
                }
                RoomPanel { id: roomPanel; width: parent.width; visible: multiplayerBridge.active }
                Grid {
                    id: panels
                    width: parent.width
                    columns: root.compact ? 1 : 2
                    columnSpacing: 14; rowSpacing: 14
                    FriendsRail { width: root.compact ? panels.width : Math.min(300 * GlassTheme.scale, panels.width * 0.32); visible: !root.compact || !socialBridge.peerId }
                    FriendChat { width: root.compact ? panels.width : panels.width - Math.min(300 * GlassTheme.scale, panels.width * 0.32) - 14; compact: root.compact; availableHeight: root.height - (invitesArea.visible ? invitesArea.height + 14 : 0) - (roomPanel.visible ? roomPanel.height + 14 : 0) - 24; visible: !root.compact || !!socialBridge.peerId }
                }
            }
        }
    }
}
