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
    readonly property bool readyToInvite: (multiplayerBridge.role === "hosting" || multiplayerBridge.role === "waiting_world") && roomSyncBridge.hostReady && !multiplayerBridge.locked && !!multiplayerBridge.roomCode
    readonly property var peer: socialBridge.friends.filter(function(f) { return f.accountId === socialBridge.peerId; })[0] || ({})
    padding: 20
    function send() {
        if (composer.text.trim() && composer.text.length <= 1000) { socialBridge.sendMessage(composer.text); composer.text = ""; }
    }
    Connections {
        target: socialBridge
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
        }
        Item {
            id: chatHeading
            width: parent.width; height: Math.max(heading.implicitHeight, invite.visible ? invite.height : 0, chatAvatar.height)
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
                anchors.right: parent.right; visible: !!socialBridge.peerId && socialBridge.peerOnline && root.readyToInvite
                label: Legacy.Tr.phrase("Mời vào phòng"); primary: true
                clickable: !socialBridge.inviteBusy
                onClicked: socialBridge.inviteFriend(socialBridge.peerId)
            }
        }
        Column {
            id: inviteHelp
            visible: !!socialBridge.peerId
            width: parent.width; spacing: 6
            GuideButton { topicId: "invite"; label: Legacy.Tr.phrase("Cách mời bạn vào phòng") }
            PaymentText {
                width: parent.width
                visible: !root.readyToInvite || !socialBridge.peerOnline
                color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption
                text: multiplayerBridge.role === "joined" ? Legacy.Tr.phrase("Rời phòng hiện tại để mở phòng của bạn.")
                    : hostBridge.details.active && !roomSyncBridge.hostReady ? Legacy.Tr.phrase("Chờ phòng và modpack sẵn sàng trước khi gửi lời mời.")
                    : multiplayerBridge.locked ? Legacy.Tr.phrase("Phòng đang khóa nhận khách mới. Mở khóa trong Tùy chọn phòng để mời bạn.")
                    : multiplayerBridge.active && !socialBridge.peerOnline ? Legacy.Tr.phrase("Người bạn này đang ngoại tuyến. Nhờ họ mở launcher để nhận lời mời.")
                    : Legacy.Tr.phrase("Bấm Tạo phòng ở phía trên. Khi phòng sẵn sàng, bạn có thể mời người đang trực tuyến.")
            }
        }
        InertialList {
            id: chatScroll
            objectName: "chatScroll"
            visible: root.chatExpanded
            width: parent.width; height: root.compact ? Math.max(40 * GlassTheme.scale, root.availableHeight - backRow.height - chatHeading.height - inviteHelp.height - 12 - composerRow.height - chatFooter.height - 40 - 60) : 250 * GlassTheme.scale
            spacing: 2
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
            delegate: Item {
                id: line
                required property var modelData
                required property int index
                objectName: "chatMessage-" + index
                width: chatScroll.width
                height: body.y + body.height + (failedRow.visible ? failedRow.height + 4 : 0) + 2
                opacity: modelData.state === "sending" ? 0.55 : 1
                readonly property real gap: modelData.grouped ? 0 : 10
                readonly property var author: modelData.mine ? socialBridge.account : root.peer
                Rectangle { anchors.fill: parent; anchors.margins: -2; radius: 6; color: GlassTheme.alpha(GlassTheme.raised, lineHover.hovered ? 0.5 : 0) }
                HoverHandler { id: lineHover }
                SocialAvatar { y: line.gap; visible: !modelData.grouped; size: 34; showPresence: false; playerName: line.author.name || ""; source: line.author.avatarUrl || ""; decor: line.author.decor || "none" }
                Row {
                    id: header
                    visible: !modelData.grouped
                    x: 46; y: line.gap; spacing: 8
                    PaymentText { id: authorName; text: line.author.name || ""; font.weight: Font.DemiBold; color: modelData.mine ? GlassTheme.accent : GlassTheme.brand; wrapMode: Text.NoWrap }
                    PaymentText { y: authorName.baselineOffset - baselineOffset; text: Qt.formatDateTime(new Date(modelData.time * 1000), "dd/MM hh:mm"); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; wrapMode: Text.NoWrap }
                }
                PaymentText {
                    id: body
                    x: 46; y: modelData.grouped ? 0 : line.gap + header.height + 2
                    width: parent.width - x
                    text: modelData.text
                    color: modelData.state === "failed" ? GlassTheme.danger : GlassTheme.text
                }
                Row {
                    id: failedRow
                    visible: modelData.state === "failed"
                    x: 46; y: body.y + body.height + 4; spacing: 8
                    PaymentText { anchors.verticalCenter: parent.verticalCenter; text: Legacy.Tr.phrase("Chưa gửi được."); color: GlassTheme.danger; font.pixelSize: GlassTheme.fontCaption; wrapMode: Text.NoWrap }
                    Button { objectName: "retryChat-" + line.index; quiet: true; height: 24; label: Legacy.Tr.phrase("Thử lại"); onClicked: socialBridge.retryMessage(modelData.id) }
                    Button { quiet: true; height: 24; label: Legacy.Tr.phrase("Xoá"); onClicked: socialBridge.discardMessage(modelData.id) }
                }
            }
        }
        Row {
            id: composerRow
            visible: !!socialBridge.peerId && root.chatExpanded
            width: parent.width; spacing: 8
            Input { id: composer; objectName: "chatComposer"; width: parent.width - sendButton.width - 8; placeholder: socialBridge.peerName ? Legacy.Tr.phrase("Nhắn %1").arg(socialBridge.peerName) : Legacy.Tr.phrase("Nhắn tin…"); onAccepted: root.send() }
            Button { id: sendButton; objectName: "sendChat"; height: composer.height; label: Legacy.Tr.phrase("Gửi"); primary: true; clickable: !!composer.text.trim() && composer.text.length <= 1000; onClicked: root.send() }
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
        PaymentText { width: parent.width; visible: !socialBridge.peerId; text: Legacy.Tr.phrase("Chọn bạn trong danh sách để mời vào phòng. Lời mời nhận được sẽ hiện ngay phía trên."); color: GlassTheme.muted }
        Button { objectName: "showOptionalChat"; visible: !!socialBridge.peerId; label: root.chatExpanded ? Legacy.Tr.phrase("Thu gọn nhắn tin") : Legacy.Tr.phrase("Nhắn tin · tuỳ chọn"); quiet: true; onClicked: root.chatExpanded = !root.chatExpanded }
    }
}
