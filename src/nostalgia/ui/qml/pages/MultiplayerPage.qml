import QtQuick
import "../"

/*
  CHƠI CHUNG: hai tấm — MỞ PHÒNG (host) và VÀO PHÒNG (bạn). Không cần thuê server, không cần
  mod: host mở "Open to LAN" trong game, launcher đẩy world qua relay; bạn nhập mã, world hiện
  trong tab LAN của Minecraft như thể cùng nhà.
*/
Item {
    id: page
    signal navigate(int pageIndex)
    property string failure: ""
    function joinRoom(code) {
        if (typeof roomSyncBridge !== "undefined") roomSyncBridge.join(code);
        else multiplayerBridge.join(code);
    }

    Connections {
        target: typeof roomSyncBridge !== "undefined" ? roomSyncBridge : null
        function onFailed(message) { page.failure = message; }
    }

    Connections {
        target: multiplayerBridge
        function onFailed(message) { page.failure = message; }
        function onStatusChanged() { if (multiplayerBridge.active) page.failure = ""; }
    }

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: pageTitle.height + subtitle.implicitHeight + 8
        PageTitle {
            id: pageTitle
            anchors { left: parent.left; top: parent.top }
            caption: Tr.phrase("Chơi chung")
        }
        Text {
            id: subtitle
            width: parent.width; wrapMode: Text.WordWrap
            anchors { left: parent.left; top: pageTitle.bottom; topMargin: 6 }
            text: "Mở LAN, gửi mã và chơi cùng bạn bè khác mạng."
            color: Theme.textMuted; font.pixelSize: Theme.fontBody
        }
    }

    Rectangle {
        id: failureBar
        anchors { top: header.bottom; left: parent.left; right: parent.right; margins: Theme.gap; topMargin: 4 }
        height: page.failure ? failureText.implicitHeight + 16 : 0
        visible: page.failure !== ""
        radius: 0; color: "#33ff5555"; border.color: "#80ff5555"
        Text {
            id: failureText
            width: parent.width - 24; wrapMode: Text.WordWrap
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            text: page.failure; color: Theme.text; font.pixelSize: Theme.fontBody
        }
    }

    Flickable {
        anchors { top: failureBar.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: 10 }
        id: scroll
        objectName: "multiplayerScroll"
        clip: true; contentHeight: panels.height; boundsBehavior: Flickable.StopAtBounds
        Flow {
        id: panels
        width: scroll.width; spacing: Theme.gap

        // ----- MỞ PHÒNG -----
        Panel {
            id: hostPanel
            visible: multiplayerBridge.role !== "joined"
            width: panels.width >= 900 && multiplayerBridge.role === "idle" ? (panels.width - Theme.gap) / 2 : panels.width
            height: contentTop + hostContent.height + Theme.pad
            title: "MỞ PHÒNG"
            readonly property bool hosting: multiplayerBridge.role === "hosting"
            readonly property bool waiting: multiplayerBridge.role === "waiting_world"

            Column {
                id: hostContent
                anchors { left: parent.left; right: parent.right }
                spacing: 14
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: Tr.phrase("1. Chạy game, vào world.\n2. Bấm Esc → Open to LAN → Start LAN World.\n3. Bấm Mở phòng ở đây rồi đọc mã cho bạn.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.35
                }
                ActionButton {
                    objectName: "hostButton"
                    visible: !hostPanel.hosting && !hostPanel.waiting
                    clickable: multiplayerBridge.role === "idle"
                    label: Tr.phrase("Mở phòng")
                    onClicked: multiplayerBridge.startHosting()
                }
                Row {
                    visible: hostPanel.waiting; spacing: 10
                    StatusPill { dotColor: Theme.accent; pulsing: true; text: Tr.phrase("Đang chờ bạn Open to LAN trong game...") }
                    ActionButton { primary: false; label: Tr.phrase("Huỷ"); onClicked: multiplayerBridge.stop() }
                }
                Column {
                    visible: hostPanel.hosting; spacing: 10; width: parent.width
                    Text { text: Tr.phrase("Mã phòng — gửi cho bạn:"); color: Theme.textMuted; font.pixelSize: Theme.fontBody }
                    Rectangle {
                        width: parent.width; height: 56; radius: 0
                        color: "#1a2b1f"; border.color: Theme.accent
                        Text {
                            objectName: "roomCodeText"
                            anchors.centerIn: parent
                            text: multiplayerBridge.roomCodeSpaced
                            color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true; font.letterSpacing: 2
                            font.family: "monospace"
                        }
                    }
                    Flow {
                        width: parent.width; spacing: 8
                        ActionButton { primary: false; label: Tr.phrase("Chép mã"); onClicked: multiplayerBridge.copyRoomCode() }
                        ActionButton {
                            primary: false
                            label: multiplayerBridge.locked ? Tr.phrase("Mở lại cửa") : Tr.phrase("Khoá phòng")
                            onClicked: multiplayerBridge.setLocked(!multiplayerBridge.locked)
                        }
                        ActionButton { primary: false; label: Tr.phrase("Đóng phòng"); onClicked: multiplayerBridge.stop() }
                    }
                    Flow {
                        width: parent.width; spacing: 10
                        StatusPill { glyph: "▣"; text: multiplayerBridge.worldName }
                        StatusPill { dotColor: Theme.accent; text: multiplayerBridge.joinerCount + Tr.phrase(" người đang vào") }
                        StatusPill { visible: multiplayerBridge.locked; glyph: "🔒"; text: Tr.phrase("Đã khoá: không nhận thêm") }
                    }
                    Text {
                        width: parent.width; wrapMode: Text.WordWrap
                        text: Tr.phrase("Mã chỉ sống khi phòng mở. Khoá phòng khi đủ người: ai có mã cũng không vào thêm được.")
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody
                    }
                    Loader {
                        width: parent.width
                        height: active && item ? item.implicitHeight : 0
                        active: hostPanel.hosting && typeof roomSyncBridge !== "undefined"
                        sourceComponent: Component { RoomSyncCard { hostMode: true } }
                    }
                }
            }
        }

        // ----- VÀO PHÒNG -----
        Panel {
            id: joinPanel
            visible: multiplayerBridge.role === "idle" || multiplayerBridge.role === "joined"
            width: panels.width >= 900 && multiplayerBridge.role === "idle" ? (panels.width - Theme.gap) / 2 : panels.width
            height: contentTop + joinContent.height + Theme.pad
            title: "VÀO PHÒNG"
            readonly property bool joined: multiplayerBridge.role === "joined"

            Column {
                id: joinContent
                anchors { left: parent.left; right: parent.right }
                spacing: 14
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: Tr.phrase("1. Nhập mã bạn gửi rồi bấm Vào phòng.\n2. Chạy game → Multiplayer: world của bạn hiện trong danh sách LAN.\n3. Bấm vào để chơi. Xong thì bấm Rời phòng.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody; lineHeight: 1.35
                }
                Column {
                    visible: !joinPanel.joined; spacing: 10
                    RoomCodeInput {
                        id: codeField
                        objectName: "roomCodeField"
                        onSubmitted: if (complete && multiplayerBridge.role === "idle") page.joinRoom(code)
                    }
                    Row {
                        spacing: 8
                        ActionButton {
                            objectName: "joinButton"
                            label: Tr.phrase("Vào phòng")
                            clickable: multiplayerBridge.role === "idle" && codeField.complete
                            onClicked: page.joinRoom(codeField.code)
                        }
                        ActionButton {
                            primary: false; label: Tr.phrase("Dán")
                            onClicked: codeField.setCode(multiplayerBridge.clipboardText())
                        }
                        ActionButton {
                            primary: false; label: Tr.phrase("Xoá")
                            visible: codeField.code.length > 0
                            onClicked: codeField.clear()
                        }
                    }
                    Text {
                        width: parent.width; wrapMode: Text.WordWrap
                        text: codeField.complete ? Tr.phrase("Đủ 18 ký tự — bấm Vào phòng hoặc Enter.") : Tr.phrase("Gõ hoặc dán mã bạn gửi: 3 nhóm, mỗi nhóm 6 ký tự.")
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody
                    }
                }
                Column {
                    visible: joinPanel.joined; spacing: 10; width: parent.width
                    StatusPill { dotColor: Theme.accent; pulsing: true; text: "Đã nối phòng" }
                    Text {
                        width: parent.width; wrapMode: Text.WordWrap
                        text: Tr.phrase("Cổng cục bộ 127.0.0.1:") + multiplayerBridge.localPort + Tr.phrase(" — chỉ máy này thấy.")
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody
                    }
                    Text {
                        width: parent.width; wrapMode: Text.WordWrap
                        text: "Nếu modpack không hiện mục LAN: Multiplayer → Direct Connection → dán địa chỉ ở trên. Cần cùng Minecraft, loader và bộ mod với host."
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody
                    }
                    Flow {
                        width: parent.width; spacing: 8
                        ActionButton { objectName: "copyLocalAddressButton"; primary: false; label: "Chép địa chỉ kết nối"; onClicked: multiplayerBridge.copyLocalAddress() }
                        ActionButton { primary: false; label: Tr.phrase("Rời phòng"); onClicked: { multiplayerBridge.stop(); codeField.clear(); } }
                        ActionButton {
                            visible: typeof roomSyncBridge !== "undefined" && roomSyncBridge.configured
                            primary: false; label: "Kiểm tra modpack của phòng"
                            clickable: typeof roomSyncBridge !== "undefined" && !roomSyncBridge.busy
                            onClicked: roomSyncBridge.checkRoomPack()
                        }
                    }
                    Loader {
                        width: parent.width
                        height: active && item ? item.implicitHeight : 0
                        active: joinPanel.joined && typeof roomSyncBridge !== "undefined" && !!roomSyncBridge.offer.name
                        sourceComponent: Component { RoomSyncCard {} }
                    }
                }
            }
        }
        }
    }
}
