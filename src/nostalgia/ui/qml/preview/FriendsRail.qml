import QtQuick
import "../" as Legacy

Glass {
    id: root
    objectName: "friendsRail"
    property bool adding: false
    property bool requestsExpanded: false
    implicitHeight: contents.implicitHeight + 32
    height: implicitHeight
    padding: 16
    Column {
        id: contents
        width: parent.width; spacing: 10
        Item {
            width: parent.width; height: add.height
            PaymentText { width: parent.width - add.width - 10; anchors.verticalCenter: parent.verticalCenter; text: Legacy.Tr.phrase("Bạn bè · ") + socialBridge.friends.length; font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold }
            Button { id: add; objectName: "showAddFriend"; anchors.right: parent.right; width: 40; label: root.adding ? "−" : "+"; quiet: true; Accessible.name: Legacy.Tr.phrase("Thêm bạn"); onClicked: root.adding = !root.adding }
        }
        Column {
            visible: root.adding
            width: parent.width; spacing: 8
            Input { id: friendCode; objectName: "friendCodeInput"; width: parent.width; placeholder: Legacy.Tr.phrase("Mã kết bạn"); onAccepted: socialBridge.requestFriend(text) }
            Button { objectName: "requestFriend"; width: parent.width; label: Legacy.Tr.phrase("Gửi yêu cầu"); clickable: !!friendCode.text.trim() && !socialBridge.busy; onClicked: socialBridge.requestFriend(friendCode.text) }
            Button { label: Legacy.Tr.phrase("Chép mã của tôi"); quiet: true; onClicked: socialBridge.copyFriendCode() }
        }
        PaymentText { width: parent.width; visible: !socialBridge.friends.length; text: Legacy.Tr.phrase("Bấm + để thêm người bạn đầu tiên."); color: GlassTheme.muted }
        InertialList {
            id: friends
            objectName: "friendsList"
            width: parent.width; height: Math.min(count * (62 * GlassTheme.scale + 6), 340 * GlassTheme.scale)
            spacing: 6
            model: socialBridge.friends
    delegate: Button {
    required property var modelData
        objectName: "friend-" + modelData.accountId
        width: friends.width
        height: Math.max(labels.implicitHeight + 20, 62 * GlassTheme.scale)
        label: ""
        selected: socialBridge.peerId === modelData.accountId
        quiet: true
        Accessible.name: modelData.name + (modelData.online ? Legacy.Tr.phrase(", trực tuyến") : Legacy.Tr.phrase(", ngoại tuyến"))
        onClicked: socialBridge.selectFriend(modelData.accountId)
        SocialAvatar { objectName: "friendAvatar-" + modelData.accountId; x: 10; anchors.verticalCenter: parent.verticalCenter; size: 40 * GlassTheme.scale; playerName: modelData.name; source: modelData.avatarUrl || ""; online: modelData.online; decor: modelData.decor || "none"; clickable: true; onClicked: socialProfileDialog.showFor(modelData.accountId) }
        Column {
            id: labels
            x: 64 * GlassTheme.scale; y: 10; width: parent.width - x - 12; spacing: 4
            PaymentText { width: parent.width; text: modelData.name + (Legacy.Tr.phrase(modelData.badge) ? "  ✦" : ""); color: modelData.accent === "emerald" ? "#60ae7b" : modelData.accent === "amber" ? "#daa86c" : modelData.accent === "amethyst" ? "#b66ba9" : GlassTheme.text; font.weight: Font.DemiBold }
            PaymentText { width: parent.width; text: modelData.online ? Legacy.Tr.phrase("●  Trực tuyến") : Legacy.Tr.phrase("○  Ngoại tuyến"); color: modelData.online ? GlassTheme.brand : GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        }
    }
        }
        Button { objectName: "showFriendRequests"; visible: socialBridge.requests.length > 0; width: parent.width; quiet: true; label: Legacy.Tr.phrase("Yêu cầu · ") + socialBridge.requests.length + (root.requestsExpanded ? "  ↑" : "  ↓"); onClicked: root.requestsExpanded = !root.requestsExpanded }
        Column {
            visible: root.requestsExpanded
            width: parent.width; spacing: 10
            Repeater {
                model: socialBridge.requests
                Column {
                    width: contents.width; spacing: 8
                    Row { width: parent.width; spacing: 10
                        SocialAvatar { playerName: modelData.name; source: modelData.avatarUrl || ""; online: modelData.online; showPresence: false; size: 32 }
                        PaymentText { width: parent.width - 42; anchors.verticalCenter: parent.verticalCenter; text: modelData.name + (modelData.incoming ? Legacy.Tr.phrase(" muốn kết bạn") : Legacy.Tr.phrase(" · Đã gửi")) }
                    }
                    Flow {
                        width: parent.width; spacing: 8
                        Button { visible: modelData.incoming; label: Legacy.Tr.phrase("Chấp nhận"); clickable: !socialBridge.busy; onClicked: socialBridge.acceptFriend(modelData.accountId) }
                        Button { label: modelData.incoming ? Legacy.Tr.phrase("Từ chối") : Legacy.Tr.phrase("Huỷ"); quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.removeFriend(modelData.accountId) }
                    }
                }
            }
        }
    }
}
