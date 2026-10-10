import QtQuick

/*
  Ô ở vị trí "FRIENDS" của bản mẫu: lối tắt sang CHƠI CHUNG. Danh sách bạn bè (presence)
  chưa làm — cần backend có chữ ký — nên không bịa người đang online.
*/
Panel {
    id: root
    signal openMultiplayer()

    title: Tr.phrase("BẠN BÈ")

    Column {
        anchors.fill: parent
        spacing: 10

        Text {
            width: parent.width
            text: multiplayerBridge.active ? (multiplayerBridge.role === "joined" ? Tr.phrase("Bạn đang trong phòng của bạn bè.") : Tr.phrase("Phòng của bạn đang mở — ") + multiplayerBridge.joinerCount + Tr.phrase(" người đang vào."))
                                             : Tr.phrase("Mở phòng rồi gửi mã cho bạn, hoặc nhập mã bạn gửi để vào.")
            color: Theme.textMuted; font.pixelSize: Theme.fontBody; wrapMode: Text.WordWrap
        }
        ActionButton {
            label: multiplayerBridge.active ? Tr.phrase("Xem phòng") : Tr.phrase("Chơi chung")
            primary: false
            onClicked: root.openMultiplayer()
        }
    }
}
