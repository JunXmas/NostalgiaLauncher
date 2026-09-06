import QtQuick

/*
  Ô ở vị trí "FRIENDS" của bản mẫu.

  Danh sách bạn bè chỉ có nghĩa khi đã có phần chơi chung, mà phần đó chưa làm. Bịa bốn người
  bạn đang online là nói dối ngay trên màn hình chính, nên ở đây nói thẳng tình trạng.
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
            text: "Phần Chơi chung chưa làm xong, nên chưa có danh sách bạn bè."
            color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap
        }
        ActionButton {
            label: "Xem Chơi chung"
            primary: false
            onClicked: root.openMultiplayer()
        }
    }
}
