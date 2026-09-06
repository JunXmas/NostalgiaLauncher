import QtQuick

/*
  Ô hồ sơ ở cột phải.

  Bản mẫu có "Level 24 / 2300 XP" — Minecraft không có cấp độ người chơi kiểu đó và lõi cũng
  không có dữ liệu ấy, nên ở đây hiển thị những gì CÓ THẬT: tên, loại tài khoản, mã người
  chơi. Chưa có tài khoản thì đưa luôn ô để thêm, chứ không vẽ một người dùng giả.
*/
Panel {
    id: root
    property string playerName: ""
    property string accountKind: ""
    property string playerUuid: ""
    signal addAccountRequested(string name)

    title: "HỒ SƠ"

    Column {
        anchors.fill: parent
        spacing: 12

        Row {
            spacing: 12
            visible: root.playerName.length > 0
            Rectangle {
                width: 52; height: 52; radius: 9; color: Theme.accentDeep
                Text {
                    anchors.centerIn: parent
                    text: root.playerName ? root.playerName.charAt(0).toUpperCase() : ""
                    color: "white"; font.pixelSize: 24; font.bold: true
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Text { text: root.playerName; color: Theme.text; font.pixelSize: 16; font.bold: true }
                Text {
                    text: root.accountKind === "microsoft" ? "Tài khoản Microsoft" : "Tài khoản offline"
                    color: Theme.textMuted; font.pixelSize: 11
                }
            }
        }

        Text {
            visible: root.playerName.length > 0
            width: parent.width
            text: root.playerUuid
            color: Theme.textMuted; font.pixelSize: 9; elide: Text.ElideMiddle
        }

        // Chưa có tài khoản: ô nhập ngay tại chỗ, để app dùng được mà không phải đi đâu khác.
        Column {
            visible: root.playerName.length === 0
            width: parent.width
            spacing: 9

            Text {
                width: parent.width
                text: "Chưa có tài khoản. Nhập tên để chơi ngoại tuyến:"
                color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap
            }
            TextField {
                id: nameField
                width: parent.width
                placeholder: "Tên trong game"
                onAccepted: root.addAccountRequested(text)
            }
            ActionButton {
                width: parent.width
                label: "Thêm tài khoản"
                onClicked: root.addAccountRequested(nameField.text)
            }
        }
    }
}
