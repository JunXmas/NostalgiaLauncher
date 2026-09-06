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

    Connections {
        target: multiplayerBridge
        function onFailed(message) { page.failure = message; }
        function onStatusChanged() { if (multiplayerBridge.active) page.failure = ""; }
    }

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 58
        Text {
            anchors { left: parent.left; top: parent.top }
            text: "Chơi chung"; color: Theme.text; font.pixelSize: 22; font.bold: true
        }
        Text {
            anchors { left: parent.left; top: parent.top; topMargin: 32 }
            text: "Không cần thuê server, không cần mod, khác mạng vẫn chơi được."
            color: Theme.textMuted; font.pixelSize: 12
        }
    }

    Rectangle {
        id: failureBar
        anchors { top: header.bottom; left: parent.left; right: parent.right; margins: Theme.gap; topMargin: 4 }
        height: page.failure ? 34 : 0
        visible: page.failure !== ""
        radius: 6; color: "#33ff5555"; border.color: "#80ff5555"
        Text {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            text: page.failure; color: Theme.text; font.pixelSize: 12
        }
    }

    Row {
        anchors { top: failureBar.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: 10 }
        spacing: Theme.gap

        // ----- MỞ PHÒNG -----
        Panel {
            id: hostPanel
            width: (parent.width - Theme.gap) / 2; height: parent.height
            title: "MỞ PHÒNG"
            readonly property bool hosting: multiplayerBridge.role === "hosting"
            readonly property bool waiting: multiplayerBridge.role === "waiting_world"

            Column {
                anchors { left: parent.left; right: parent.right }
                spacing: 14
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: "1. Chạy game, vào world.\n2. Bấm Esc → Open to LAN → Start LAN World.\n3. Bấm Mở phòng ở đây rồi đọc mã cho bạn."
                    color: Theme.textMuted; font.pixelSize: 12; lineHeight: 1.35
                }
                ActionButton {
                    objectName: "hostButton"
                    visible: !hostPanel.hosting && !hostPanel.waiting
                    clickable: multiplayerBridge.role === "idle"
                    label: "Mở phòng"
                    onClicked: multiplayerBridge.startHosting()
                }
                Row {
                    visible: hostPanel.waiting; spacing: 10
                    StatusPill { dotColor: Theme.accent; pulsing: true; text: "Đang chờ bạn Open to LAN trong game..." }
                    ActionButton { primary: false; label: "Huỷ"; onClicked: multiplayerBridge.stop() }
                }
                Column {
                    visible: hostPanel.hosting; spacing: 10; width: parent.width
                    Text { text: "Mã phòng — gửi cho bạn:"; color: Theme.textMuted; font.pixelSize: 12 }
                    Rectangle {
                        width: parent.width; height: 56; radius: 8
                        color: "#1a2b1f"; border.color: Theme.accent
                        Text {
                            objectName: "roomCodeText"
                            anchors.centerIn: parent
                            text: multiplayerBridge.roomCodeSpaced
                            color: Theme.text; font.pixelSize: 22; font.bold: true; font.letterSpacing: 2
                            font.family: "monospace"
                        }
                    }
                    Row {
                        spacing: 8
                        ActionButton { primary: false; label: "Chép mã"; onClicked: multiplayerBridge.copyRoomCode() }
                        ActionButton {
                            primary: false
                            label: multiplayerBridge.locked ? "Mở lại cửa" : "Khoá phòng"
                            onClicked: multiplayerBridge.setLocked(!multiplayerBridge.locked)
                        }
                        ActionButton { primary: false; label: "Đóng phòng"; onClicked: multiplayerBridge.stop() }
                    }
                    Row {
                        spacing: 10
                        StatusPill { glyph: "▣"; text: multiplayerBridge.worldName }
                        StatusPill { dotColor: Theme.accent; text: multiplayerBridge.joinerCount + " người đang vào" }
                        StatusPill { visible: multiplayerBridge.locked; glyph: "🔒"; text: "Đã khoá: không nhận thêm" }
                    }
                    Text {
                        width: parent.width; wrapMode: Text.WordWrap
                        text: "Mã chỉ sống khi phòng mở. Khoá phòng khi đủ người: ai có mã cũng không vào thêm được."
                        color: Theme.textMuted; font.pixelSize: 11
                    }
                }
            }
        }

        // ----- VÀO PHÒNG -----
        Panel {
            id: joinPanel
            width: (parent.width - Theme.gap) / 2; height: parent.height
            title: "VÀO PHÒNG"
            readonly property bool joined: multiplayerBridge.role === "joined"

            Column {
                anchors { left: parent.left; right: parent.right }
                spacing: 14
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: "1. Nhập mã bạn gửi rồi bấm Vào phòng.\n2. Chạy game → Multiplayer: world của bạn hiện trong danh sách LAN.\n3. Bấm vào để chơi. Xong thì bấm Rời phòng."
                    color: Theme.textMuted; font.pixelSize: 12; lineHeight: 1.35
                }
                Row {
                    visible: !joinPanel.joined; spacing: 8
                    TextField {
                        id: codeField
                        objectName: "roomCodeField"
                        width: 300
                        placeholder: "Mã phòng 18 ký tự"
                        onAccepted: multiplayerBridge.join(text)
                    }
                    ActionButton {
                        objectName: "joinButton"
                        label: "Vào phòng"
                        clickable: multiplayerBridge.role === "idle" && codeField.text.trim().length > 0
                        onClicked: multiplayerBridge.join(codeField.text)
                    }
                }
                Column {
                    visible: joinPanel.joined; spacing: 10; width: parent.width
                    Row {
                        spacing: 10
                        StatusPill { dotColor: Theme.accent; pulsing: true; text: "Đã nối: mở game, vào Multiplayer, chọn world trong mục LAN" }
                    }
                    Text {
                        text: "Cổng cục bộ 127.0.0.1:" + multiplayerBridge.localPort + " — chỉ máy này thấy."
                        color: Theme.textMuted; font.pixelSize: 11
                    }
                    ActionButton { primary: false; label: "Rời phòng"; onClicked: multiplayerBridge.stop() }
                }
            }
        }
    }
}
