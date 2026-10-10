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
    property bool chatExpanded: false
    readonly property var peer: socialBridge.friends.filter(function(f) { return f.accountId === socialBridge.peerId; })[0] || ({})
    padding: 20
    function send() {
        if (composer.text.trim() && !socialBridge.chatBusy) socialBridge.sendMessage(composer.text);
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
            var follow = !root.lastMessageId || latest.mine || chatScroll.contentY + chatScroll.height >= chatScroll.originY + chatScroll.contentHeight - 80;
            root.lastMessageId = latest.id;
            if (follow) Qt.callLater(function() { chatScroll.positionViewAtEnd(); });
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
            Button { id: backButton; objectName: "backToFriends"; quiet: true; label: Legacy.Tr.phrase("← Bạn bè"); onClicked: socialBridge.selectFriend("") }
            Button { anchors.right: parent.right; visible: !multiplayerBridge.active && !hostBridge.details.active; label: Legacy.Tr.phrase("Mở phòng"); primary: true; onClicked: hostBridge.openSetup() }
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
                PaymentText { width: parent.width; text: socialBridge.peerName || Legacy.Tr.phrase("Cùng nhau chơi"); font.pixelSize: GlassTheme.fontLead; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; visible: !!socialBridge.peerId; text: socialBridge.peerOnline ? Legacy.Tr.phrase("● Trực tuyến") : Legacy.Tr.phrase("○ Ngoại tuyến"); color: socialBridge.peerOnline ? GlassTheme.brand : GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
            Button {
                id: invite
                objectName: "inviteSelectedFriend"
                anchors.right: parent.right; visible: !!socialBridge.peerId
                label: multiplayerBridge.active || hostBridge.details.active ? Legacy.Tr.phrase("Mời vào room") : Legacy.Tr.phrase("Mở phòng"); primary: true
                clickable: !socialBridge.inviteBusy && ((!multiplayerBridge.active && !hostBridge.details.active) || ((multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") && roomSyncBridge.hostReady && socialBridge.peerOnline && !multiplayerBridge.locked))
                onClicked: { if (multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") socialBridge.inviteFriend(socialBridge.peerId); else hostBridge.openSetup(); }
            }
        }
        Column {
            id: inviteHelp
            visible: !!socialBridge.peerId
            width: parent.width; spacing: 6
            GuideButton { topicId: "invite"; label: Legacy.Tr.phrase("Mời bạn vào room") }
            PaymentText {
                width: parent.width
                visible: multiplayerBridge.role !== "hosting" || !roomSyncBridge.hostReady || !socialBridge.peerOnline
                color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
                text: multiplayerBridge.role === "joined" ? Legacy.Tr.phrase("Rời phòng hiện tại để mở phòng của bạn.")
                    : multiplayerBridge.role === "waiting_world" ? Legacy.Tr.phrase("Mời bạn vào room trước, rồi khởi chạy Minecraft và mở LAN khi sẵn sàng.")
                    : hostBridge.details.active && !roomSyncBridge.hostReady ? Legacy.Tr.phrase("Chờ phòng và modpack sẵn sàng trước khi gửi lời mời.")
                    : multiplayerBridge.role === "hosting" && !socialBridge.peerOnline ? Legacy.Tr.phrase("Bạn đang ngoại tuyến. Người nhận cần mở launcher để nhận lời mời.")
                    : Legacy.Tr.phrase("Bấm Mở phòng, chọn bản chơi và tạo room để mời bạn trước khi khởi chạy Minecraft.")
            }
        }
        InertialList {
            id: chatScroll
            objectName: "chatScroll"
            visible: root.chatExpanded
            width: parent.width; height: root.compact ? Math.max(40 * GlassTheme.scale, root.availableHeight - backRow.height - chatHeading.height - inviteHelp.height - 12 - composerRow.height - chatFooter.height - 40 - 60) : 250 * GlassTheme.scale
            spacing: 10
            model: root.chatExpanded ? socialBridge.messages : []
            header: Column {
                width: chatScroll.width; spacing: 10
            PaymentText {
                width: parent.width
                visible: !!socialBridge.peerId && !socialBridge.messages.length
                text: socialBridge.peerId ? Legacy.Tr.phrase("Gửi lời chào để bắt đầu câu chuyện.") : Legacy.Tr.phrase("Chọn một người bạn để trò chuyện.")
                color: GlassTheme.muted
            }
            Column {
                width: parent.width; visible: !socialBridge.peerId; spacing: 14
                Item { width: parent.width; height: 104
                    Legacy.BlockIcon { anchors.centerIn: parent; width: 82; height: 82; block: "command"; spinning: emptyHover.hovered; glyph: "·" }
                    HoverHandler { id: emptyHover }
                }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Một lời chào, một chuyến phiêu lưu."); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontTitle; horizontalAlignment: Text.AlignHCenter }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Chọn avatar để xem hồ sơ, hoặc chọn tên một người bạn để bắt đầu trò chuyện."); color: GlassTheme.muted; horizontalAlignment: Text.AlignHCenter }
            }
            }
            delegate: Rectangle {
                required property var modelData
                required property int index
                objectName: "chatMessage-" + index
                x: modelData.mine ? chatScroll.width * 0.12 : 0
                width: chatScroll.width * 0.88
                height: messageText.implicitHeight + 22
                radius: 12
                color: GlassTheme.alpha(modelData.mine ? GlassTheme.accent : GlassTheme.raised, modelData.mine ? 0.16 : 0.7)
                PaymentText { id: messageText; x: 12; y: 11; width: parent.width - 24; text: modelData.text }
            }
        }
        Row {
            id: composerRow
            visible: !!socialBridge.peerId && root.chatExpanded
            width: parent.width; spacing: 8
            Input { id: composer; objectName: "chatComposer"; width: parent.width - sendButton.width - 8; placeholder: Legacy.Tr.phrase("Nhắn tin…"); onAccepted: root.send() }
            Button { id: sendButton; objectName: "sendChat"; height: composer.height; label: socialBridge.chatBusy ? Legacy.Tr.phrase("Đang gửi…") : Legacy.Tr.phrase("Gửi"); primary: true; clickable: !!composer.text.trim() && composer.text.length <= 1000 && !socialBridge.chatBusy; onClicked: root.send() }
        }
        Item {
            id: chatFooter
            visible: !!socialBridge.peerId && root.chatExpanded
            width: parent.width; height: more.height
            PaymentText { width: parent.width - more.width - 8; anchors.verticalCenter: parent.verticalCenter; text: Legacy.Tr.phrase("Tin nhắn lưu 30 ngày"); font.pixelSize: GlassTheme.fontCaption; color: GlassTheme.muted }
            Button { id: more; objectName: "chatOptions"; anchors.right: parent.right; width: 40; height: 30; label: "···"; quiet: true; Accessible.name: Legacy.Tr.phrase("Tùy chọn trò chuyện"); onClicked: root.optionsExpanded = !root.optionsExpanded }
        }
        Flow {
            visible: root.optionsExpanded
            width: parent.width; spacing: 8
            Button { objectName: "viewFriendProfile"; label: Legacy.Tr.phrase("Xem hồ sơ"); quiet: true; onClicked: socialProfileDialog.showFor(socialBridge.peerId) }
            Button { label: Legacy.Tr.phrase("Làm mới"); quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.refresh() }
            Button {
                label: Legacy.Tr.phrase("Chặn người chơi"); quiet: true; clickable: !socialBridge.busy
                onClicked: { var selected = socialBridge.peerId; confirmDialog.ask(Legacy.Tr.phrase("Chặn người chơi?"), Legacy.Tr.phrase("Người này sẽ không gửi chat hay lời mời cho bạn được nữa."), function() { socialBridge.blockFriend(selected); }); }
            }
        }
        PaymentText { width: parent.width; visible: !socialBridge.peerId; text: Legacy.Tr.phrase("Chọn bạn trong danh sách để mời vào room. Lời mời nhận được sẽ hiện ngay phía trên."); color: GlassTheme.muted }
        Button { objectName: "showOptionalChat"; visible: !!socialBridge.peerId; label: root.chatExpanded ? Legacy.Tr.phrase("Thu gọn nhắn tin") : Legacy.Tr.phrase("Nhắn tin · tuỳ chọn"); quiet: true; onClicked: root.chatExpanded = !root.chatExpanded }
    }
}
