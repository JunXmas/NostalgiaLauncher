import QtQuick

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
    Column {
        id: contents
        width: parent.width; spacing: 12
        Item {
            id: backRow
            visible: root.compact
            width: parent.width; height: backButton.height
            Button { id: backButton; objectName: "backToFriends"; quiet: true; label: "← Bạn bè"; onClicked: socialBridge.selectFriend("") }
            Button { anchors.right: parent.right; visible: !multiplayerBridge.active; label: "Mở phòng"; primary: true; onClicked: multiplayerBridge.startHosting() }
        }
        Item {
            id: chatHeading
            width: parent.width; height: Math.max(heading.implicitHeight, invite.height)
            Column {
                id: heading
                width: parent.width - (invite.visible ? invite.width + 12 : 0)
                spacing: 4
                PaymentText { width: parent.width; text: socialBridge.peerName || "Cùng nhau chơi"; font.pixelSize: 19 * GlassTheme.scale; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; visible: !!socialBridge.peerId; text: socialBridge.peerOnline ? "● Trực tuyến" : "○ Ngoại tuyến"; color: socialBridge.peerOnline ? GlassTheme.brand : GlassTheme.muted; font.pixelSize: 10 * GlassTheme.scale }
            }
            Button {
                id: invite
                objectName: "inviteSelectedFriend"
                anchors.right: parent.right; visible: !!socialBridge.peerId
                label: "Mời chơi"; primary: true
                clickable: multiplayerBridge.role === "hosting" && socialBridge.peerOnline && !socialBridge.busy
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
                    visible: !socialBridge.messages.length
                    text: socialBridge.peerId ? "Bắt đầu câu chuyện. Chỉ bạn bè đã chấp nhận mới gửi tin được." : "Chọn một người bạn để trò chuyện."
                    color: GlassTheme.muted
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
            PaymentText { width: parent.width - more.width - 8; anchors.verticalCenter: parent.verticalCenter; text: "Tin nhắn lưu 30 ngày"; font.pixelSize: 10 * GlassTheme.scale; color: GlassTheme.muted }
            Button { id: more; objectName: "chatOptions"; anchors.right: parent.right; width: 40; height: 30; label: "···"; quiet: true; Accessible.name: "Tùy chọn trò chuyện"; onClicked: root.optionsExpanded = !root.optionsExpanded }
        }
        Flow {
            visible: root.optionsExpanded
            width: parent.width; spacing: 8
            Button { label: "Làm mới"; quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.refresh() }
            Button {
                label: "Chặn người chơi"; quiet: true; clickable: !socialBridge.busy
                onClicked: { var selected = socialBridge.peerId; confirmDialog.ask("Chặn người chơi?", "Người này sẽ không gửi chat hay lời mời cho bạn được nữa.", function() { socialBridge.blockFriend(selected); }); }
            }
        }
    }
}
