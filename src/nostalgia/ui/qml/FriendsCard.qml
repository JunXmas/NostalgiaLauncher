import QtQuick

/*
  Ô ở vị trí "FRIENDS" của bản mẫu: lối tắt sang CHƠI CHUNG. Danh sách bạn bè (presence)
  chưa làm — cần backend có chữ ký — nên không bịa người đang online.
*/
Panel {
    id: root
    signal openMultiplayer()

    title: "BẠN BÈ"

    Column {
        anchors.fill: parent
        spacing: 10

        Text {
            width: parent.width
            text: multiplayerBridge.active ? (multiplayerBridge.role === "joined" ? "Bạn đang trong phòng của bạn bè." : "Phòng của bạn đang mở — " + multiplayerBridge.joinerCount + " người đang vào.")
                                             : "Mở phòng rồi gửi mã cho bạn, hoặc nhập mã bạn gửi để vào."
            color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap
        }
        ActionButton {
            label: multiplayerBridge.active ? "Xem phòng" : "Chơi chung"
            primary: false
            onClicked: root.openMultiplayer()
        }
    }
}
