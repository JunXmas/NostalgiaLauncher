import QtQuick

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
            PaymentText { width: parent.width - add.width - 10; anchors.verticalCenter: parent.verticalCenter; text: "Bạn bè · " + socialBridge.friends.length; font.pixelSize: GlassTheme.fontHeading; font.weight: Font.DemiBold }
            Button { id: add; objectName: "showAddFriend"; anchors.right: parent.right; width: 40; label: root.adding ? "−" : "+"; quiet: true; Accessible.name: "Thêm bạn"; onClicked: root.adding = !root.adding }
        }
        Column {
            visible: root.adding
            width: parent.width; spacing: 8
            Input { id: friendCode; objectName: "friendCodeInput"; width: parent.width; placeholder: "Mã kết bạn"; onAccepted: socialBridge.requestFriend(text) }
            Button { objectName: "requestFriend"; width: parent.width; label: "Gửi yêu cầu"; clickable: !!friendCode.text.trim() && !socialBridge.busy; onClicked: socialBridge.requestFriend(friendCode.text) }
            Button { label: "Chép mã của tôi"; quiet: true; onClicked: socialBridge.copyFriendCode() }
        }
        PaymentText { width: parent.width; visible: !socialBridge.friends.length; text: "Bấm + để thêm người bạn đầu tiên."; color: GlassTheme.muted }
        InertialScroll {
            width: parent.width
            height: Math.min(friends.implicitHeight, 340 * GlassTheme.scale)
            contentHeight: friends.implicitHeight
            Column {
                id: friends
                width: parent.width; spacing: 6
                Repeater {
                    model: socialBridge.friends
                    Button {
                        objectName: "friend-" + modelData.accountId
                        width: friends.width
                        height: labels.implicitHeight + 20
                        label: ""
                        selected: socialBridge.peerId === modelData.accountId
                        quiet: true
                        Accessible.name: modelData.name + (modelData.online ? ", trực tuyến" : ", ngoại tuyến")
                        onClicked: socialBridge.selectFriend(modelData.accountId)
                        Column {
                            id: labels
                            x: 12; y: 10; width: parent.width - 24; spacing: 4
                            PaymentText { width: parent.width; text: modelData.name + (modelData.badge ? " · " + modelData.badge : ""); color: modelData.accent === "emerald" ? "#60ae7b" : modelData.accent === "amber" ? "#daa86c" : modelData.accent === "amethyst" ? "#b66ba9" : GlassTheme.text; font.weight: Font.DemiBold }
                            PaymentText { width: parent.width; text: modelData.online ? "●  Trực tuyến" : "○  Ngoại tuyến"; color: modelData.online ? GlassTheme.brand : GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                        }
                    }
                }
            }
        }
        Button { objectName: "showFriendRequests"; visible: socialBridge.requests.length > 0; width: parent.width; quiet: true; label: "Yêu cầu · " + socialBridge.requests.length + (root.requestsExpanded ? "  ↑" : "  ↓"); onClicked: root.requestsExpanded = !root.requestsExpanded }
        Column {
            visible: root.requestsExpanded
            width: parent.width; spacing: 10
            Repeater {
                model: socialBridge.requests
                Column {
                    width: contents.width; spacing: 8
                    PaymentText { width: parent.width; text: modelData.name + (modelData.incoming ? " muốn kết bạn" : " · Đã gửi") }
                    Flow {
                        width: parent.width; spacing: 8
                        Button { visible: modelData.incoming; label: "Chấp nhận"; clickable: !socialBridge.busy; onClicked: socialBridge.acceptFriend(modelData.accountId) }
                        Button { label: modelData.incoming ? "Từ chối" : "Huỷ"; quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.removeFriend(modelData.accountId) }
                    }
                }
            }
        }
    }
}
