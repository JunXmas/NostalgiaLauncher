import QtQuick
import "../" as Legacy

Glass {
    id: root
    objectName: "friendChat"
    implicitHeight: contents.implicitHeight + 40
    height: implicitHeight
    property string lastMessageId: ""
    property string displayedPeer: ""
    property bool compact: false
    property real availableHeight: 480
    property bool optionsExpanded: false
    readonly property var peer: socialBridge.friends.filter(function(f) { return f.accountId === socialBridge.peerId; })[0] || ({})
    padding: 20
    function send() {
        if (composer.text.trim() && !socialBridge.busy) socialBridge.sendMessage(composer.text);
    }
    Connections {
        target: socialBridge
        function onMessageSent(text) { if (composer.text.trim() === text) composer.text = ""; }
        function onChanged() {
            if (root.displayedPeer !== socialBridge.peerId) {
                root.displayedPeer = socialBridge.peerId;
                chatEntrance.restart();
                composer.text = ""; root.lastMessageId = ""; root.optionsExpanded = false;
            }
            var messages = socialBridge.messages;
            var latest = messages.length ? messages[messages.length - 1] : null;
            if (!latest) { root.lastMessageId = ""; return; }
            if (latest.id === root.lastMessageId) return;
            var follow = !root.lastMessageId || latest.mine || chatScroll.contentY + chatScroll.height >= chatScroll.contentHeight - 80;
            root.lastMessageId = latest.id;
            if (follow) Qt.callLater(function() { chatScroll.contentY = Math.max(0, chatScroll.contentHeight - chatScroll.height); });
        }
    }
    NumberAnimation { id: chatEntrance; target: contents; property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
    Column {
        id: contents
        width: parent.width; spacing: 12
        Item {
            id: backRow
            visible: root.compact
            width: parent.width; height: backButton.height
            Button { id: backButton; objectName: "backToFriends"; quiet: true; label: "← Bạn bè"; onClicked: socialBridge.selectFriend("") }
            Button { anchors.right: parent.right; visible: !multiplayerBridge.active && !hostBridge.details.active; label: "Mở phòng"; primary: true; onClicked: hostBridge.openSetup() }
        }
        Item {
            id: chatHeading
            width: parent.width; height: Math.max(heading.implicitHeight, invite.height, chatAvatar.height)
            SocialAvatar { id: chatAvatar; objectName: "chatFriendAvatar"; anchors.verticalCenter: parent.verticalCenter; visible: !!socialBridge.peerId; playerName: socialBridge.peerName; source: root.peer.avatarUrl || ""; decor: root.peer.decor || "none"; online: socialBridge.peerOnline; clickable: true; onClicked: socialProfileDialog.showFor(socialBridge.peerId) }
            Column {
                id: heading
                x: chatAvatar.visible ? chatAvatar.width + 12 : 0
                width: parent.width - x - (invite.visible ? invite.width + 12 : 0)
                spacing: 4
                PaymentText { width: parent.width; text: socialBridge.peerName || "Cùng nhau chơi"; font.pixelSize: GlassTheme.fontLead; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; visible: !!socialBridge.peerId; text: socialBridge.peerOnline ? "● Trực tuyến" : "○ Ngoại tuyến"; color: socialBridge.peerOnline ? GlassTheme.brand : GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
            Button {
                id: invite
                objectName: "inviteSelectedFriend"
                anchors.right: parent.right; visible: !!socialBridge.peerId
                label: "Mời chơi"; primary: true
                clickable: multiplayerBridge.role === "hosting" && roomSyncBridge.hostReady && socialBridge.peerOnline && !socialBridge.busy
                onClicked: socialBridge.inviteFriend(socialBridge.peerId)
            }
        }
        InertialScroll {
            id: chatScroll
            objectName: "chatScroll"
            width: parent.width; height: root.compact ? Math.max(96 * GlassTheme.scale, root.availableHeight - backRow.height - chatHeading.height - composerRow.height - chatFooter.height - 40 - 60) : 250 * GlassTheme.scale
            contentHeight: messages.implicitHeight + 6
            Column {
                id: messages
                width: parent.width; spacing: 10
                PaymentText {
                    width: parent.width
                    visible: !!socialBridge.peerId && !socialBridge.messages.length
                    text: socialBridge.peerId ? "Bắt đầu câu chuyện. Chỉ bạn bè đã chấp nhận mới gửi tin được." : "Chọn một người bạn để trò chuyện."
                    color: GlassTheme.muted
                }
                Column {
                    width: parent.width; visible: !socialBridge.peerId; spacing: 14
                    Item { width: parent.width; height: 104
                        Legacy.BlockIcon { anchors.centerIn: parent; width: 82; height: 82; block: "command"; spinning: emptyHover.hovered; glyph: "·" }
                        HoverHandler { id: emptyHover }
                    }
                    PaymentText { width: parent.width; text: "Một lời chào, một chuyến phiêu lưu."; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontTitle; horizontalAlignment: Text.AlignHCenter }
                    PaymentText { width: parent.width; text: "Chọn avatar để xem hồ sơ, hoặc chọn tên một người bạn để bắt đầu trò chuyện."; color: GlassTheme.muted; horizontalAlignment: Text.AlignHCenter }
                }
                Repeater {
                    model: socialBridge.messages
                    Rectangle {
                        objectName: "chatMessage-" + index
                        x: modelData.mine ? messages.width * 0.12 : 0
                        width: messages.width * 0.88
                        height: messageText.implicitHeight + 22
                        radius: 12
                        color: GlassTheme.alpha(modelData.mine ? GlassTheme.accent : GlassTheme.raised, modelData.mine ? 0.16 : 0.7)
                        PaymentText { id: messageText; x: 12; y: 11; width: parent.width - 24; text: modelData.text }
                    }
                }
            }
        }
        Row {
            id: composerRow
            visible: !!socialBridge.peerId
            width: parent.width; spacing: 8
            Input { id: composer; objectName: "chatComposer"; width: parent.width - sendButton.width - 8; placeholder: "Nhắn tin…"; onAccepted: root.send() }
            Button { id: sendButton; objectName: "sendChat"; height: composer.height; label: "Gửi"; primary: true; clickable: !!composer.text.trim() && composer.text.length <= 1000 && !socialBridge.busy; onClicked: root.send() }
        }
        Item {
            id: chatFooter
            visible: !!socialBridge.peerId
            width: parent.width; height: more.height
            PaymentText { width: parent.width - more.width - 8; anchors.verticalCenter: parent.verticalCenter; text: "Tin nhắn lưu 30 ngày"; font.pixelSize: GlassTheme.fontCaption; color: GlassTheme.muted }
            Button { id: more; objectName: "chatOptions"; anchors.right: parent.right; width: 40; height: 30; label: "···"; quiet: true; Accessible.name: "Tùy chọn trò chuyện"; onClicked: root.optionsExpanded = !root.optionsExpanded }
        }
        Flow {
            visible: root.optionsExpanded
            width: parent.width; spacing: 8
            Button { objectName: "viewFriendProfile"; label: "Xem hồ sơ"; quiet: true; onClicked: socialProfileDialog.showFor(socialBridge.peerId) }
            Button { label: "Làm mới"; quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.refresh() }
            Button {
                label: "Chặn người chơi"; quiet: true; clickable: !socialBridge.busy
                onClicked: { var selected = socialBridge.peerId; confirmDialog.ask("Chặn người chơi?", "Người này sẽ không gửi chat hay lời mời cho bạn được nữa.", function() { socialBridge.blockFriend(selected); }); }
            }
        }
    }
}
