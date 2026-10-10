import QtQuick
import "../" as Legacy
import "FriendFilter.js" as FriendFilter

Column {
    id: root
    objectName: "roomInviteArea"
    readonly property var onlineFriends: socialBridge.friends.filter(function(friend) { return friend.online; })
    readonly property var filteredFriends: FriendFilter.filter(root.onlineFriends, search.text)
    width: parent.width; spacing: 10
    PaymentText {
        width: parent.width
        text: Legacy.Tr.phrase("Mời bạn bè") + " · " + root.onlineFriends.length
        font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold
    }
    PaymentText {
        width: parent.width
        text: root.onlineFriends.length ? Legacy.Tr.phrase("Bấm Mời vào phòng cạnh tên bạn. Người nhận chỉ cần mở launcher và chấp nhận lời mời.")
            : socialBridge.friends.length ? Legacy.Tr.phrase("Chưa có bạn trực tuyến. Nhờ bạn mở launcher và đăng nhập Google để nhận lời mời.")
            : Legacy.Tr.phrase("Thêm bạn ở tab Bạn bè trước, rồi quay lại đây để mời vào phòng.")
        color: GlassTheme.muted
    }
    FriendSearch {
        id: search; objectName: "roomFriendSearch"; width: parent.width
        visible: root.onlineFriends.length > 0
        placeholder: Legacy.Tr.phrase("Tìm bạn trực tuyến để mời…")
        onTextChanged: { friends.stopMotion(); friends.positionViewAtBeginning(); }
    }
    PaymentText { width: parent.width; visible: !!search.text.trim(); text: Legacy.Tr.phrase("Kết quả · ") + root.filteredFriends.length + " / " + root.onlineFriends.length; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
    PaymentText { objectName: "roomFriendSearchEmpty"; width: parent.width; visible: !!root.onlineFriends.length && !root.filteredFriends.length; text: Legacy.Tr.phrase("Không có bạn trực tuyến phù hợp. Thử tên khác nhé."); color: GlassTheme.muted }
    InertialList {
        id: friends
        objectName: "roomOnlineFriends"
        width: parent.width
        height: Math.min(count * (72 * GlassTheme.scale + spacing), 240 * GlassTheme.scale)
        spacing: 6; model: root.filteredFriends
        delegate: Rectangle {
            required property var modelData
            width: friends.width; height: 72 * GlassTheme.scale; radius: 12
            color: GlassTheme.alpha(GlassTheme.raised, 0.5)
            SocialAvatar { id: avatar; x: 12; anchors.verticalCenter: parent.verticalCenter; size: 36 * GlassTheme.scale; playerName: modelData.name; source: modelData.avatarUrl || ""; decor: modelData.decor || "none"; online: true }
            PaymentText { x: avatar.x + avatar.width + 10; anchors.verticalCenter: parent.verticalCenter; width: Math.max(0, (invite.visible ? invite.x : parent.width - 12) - x - 10); text: modelData.name; maximumLineCount: 2; elide: Text.ElideRight; font.weight: Font.DemiBold }
            Button {
                id: invite
                objectName: "roomInvite-" + modelData.accountId
                anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                visible: (multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") && roomSyncBridge.hostReady && !multiplayerBridge.locked
                label: Legacy.Tr.phrase("Mời vào phòng"); primary: true
                clickable: (multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") && roomSyncBridge.hostReady && !multiplayerBridge.locked && !socialBridge.inviteBusy
                onClicked: socialBridge.inviteFriend(modelData.accountId)
            }
        }
    }
    PaymentText { width: parent.width; visible: multiplayerBridge.locked; text: Legacy.Tr.phrase("Phòng đang khóa nhận khách mới. Mở khóa trong Tùy chọn phòng để mời bạn."); color: Legacy.Theme.warning }
}
