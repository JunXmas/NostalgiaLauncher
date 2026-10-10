import QtQuick
import "../" as Legacy

Column {
    id: root
    objectName: "roomInviteArea"
    readonly property var onlineFriends: socialBridge.friends.filter(function(friend) { return friend.online; })
    width: parent.width; spacing: 10
    PaymentText {
        width: parent.width
        text: Legacy.Tr.phrase("Mời bạn bè") + " · " + root.onlineFriends.length
        font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold
    }
    PaymentText {
        width: parent.width
        text: root.onlineFriends.length ? Legacy.Tr.phrase("Bấm Mời vào room cạnh tên bạn. Người nhận chỉ cần mở launcher và chấp nhận lời mời.")
            : socialBridge.friends.length ? Legacy.Tr.phrase("Chưa có bạn trực tuyến. Nhờ bạn mở launcher và đăng nhập Google để nhận lời mời.")
            : Legacy.Tr.phrase("Thêm bạn ở tab Bạn bè trước, rồi quay lại đây để mời vào room.")
        color: GlassTheme.muted
    }
    InertialList {
        id: friends
        objectName: "roomOnlineFriends"
        width: parent.width
        height: Math.min(count * (72 * GlassTheme.scale + spacing), 240 * GlassTheme.scale)
        spacing: 6; model: root.onlineFriends
        delegate: Rectangle {
            required property var modelData
            width: friends.width; height: 72 * GlassTheme.scale; radius: 12
            color: GlassTheme.alpha(GlassTheme.raised, 0.5)
            SocialAvatar { id: avatar; x: 12; anchors.verticalCenter: parent.verticalCenter; size: 36 * GlassTheme.scale; playerName: modelData.name; source: modelData.avatarUrl || ""; decor: modelData.decor || "none"; online: true }
            PaymentText { x: avatar.x + avatar.width + 10; anchors.verticalCenter: parent.verticalCenter; width: Math.max(0, invite.x - x - 10); text: modelData.name; maximumLineCount: 2; elide: Text.ElideRight; font.weight: Font.DemiBold }
            Button {
                id: invite
                objectName: "roomInvite-" + modelData.accountId
                anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                label: Legacy.Tr.phrase("Mời vào room"); primary: true
                clickable: (multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") && roomSyncBridge.hostReady && !multiplayerBridge.locked && !socialBridge.inviteBusy
                onClicked: socialBridge.inviteFriend(modelData.accountId)
            }
        }
    }
    PaymentText { width: parent.width; visible: multiplayerBridge.locked; text: Legacy.Tr.phrase("Phòng đang khóa nhận khách mới. Mở khóa trong Tùy chọn phòng để mời bạn."); color: Legacy.Theme.warning }
}
