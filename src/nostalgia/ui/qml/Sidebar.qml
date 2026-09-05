import QtQuick

/* Thanh bên. STORE của bản mẫu đã đổi thành MULTIPLAYER theo yêu cầu. */
Rectangle {
    id: root
    property int currentIndex: 0
    property string playerName: ""
    property string accountKind: ""

    color: Theme.surface
    border.color: Theme.border
    border.width: 0

    readonly property var entries: [
        { label: "TRANG CHỦ",   glyph: "⌂" },
        { label: "BẢN CHƠI",    glyph: "⛏" },
        { label: "MOD",         glyph: "⚙" },
        { label: "MÁY CHỦ",     glyph: "☷" },
        { label: "TÀI NGUYÊN",  glyph: "▤" },
        { label: "CHƠI CHUNG",  glyph: "⛶" },
        { label: "CÀI ĐẶT",     glyph: "☸" }
    ]

    Column {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: 18 }
        spacing: 2

        Row {
            spacing: 10
            Rectangle {
                width: 30; height: 30; radius: 7; color: Theme.accentDeep
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.centerIn: parent; text: "▣"; color: "white"; font.pixelSize: 17 }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                Text { text: "NOSTALGIA"; color: Theme.text; font.pixelSize: 16; font.bold: true; font.letterSpacing: 1.4 }
                Text { text: "Trình khởi động Minecraft"; color: Theme.textMuted; font.pixelSize: 9; font.letterSpacing: 0.6 }
            }
        }
    }

    Column {
        anchors { top: header.bottom; topMargin: 26; left: parent.left; right: parent.right; margins: 10 }
        spacing: 4

        Repeater {
            model: root.entries
            NavItem {
                label: modelData.label
                glyph: modelData.glyph
                selected: index === root.currentIndex
                onClicked: root.currentIndex = index
            }
        }
    }

    // Thẻ tài khoản dưới cùng. Chưa đăng nhập thì nói thẳng là chưa, không vẽ người giả.
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: version.top; margins: 14; bottomMargin: 14 }
        height: 62
        radius: Theme.radiusSmall
        color: Theme.surfaceHigh

        Row {
            anchors { fill: parent; margins: 12 }
            spacing: 10
            Rectangle {
                width: 36; height: 36; radius: 6
                color: root.playerName ? Theme.accentDeep : Theme.border
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    anchors.centerIn: parent
                    text: root.playerName ? root.playerName.charAt(0).toUpperCase() : "?"
                    color: "white"; font.pixelSize: 16; font.bold: true
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3
                Text {
                    text: root.playerName ? root.playerName : "Chưa có tài khoản"
                    color: Theme.text; font.pixelSize: 13; font.bold: true
                }
                Text {
                    text: root.playerName
                        ? (root.accountKind === "microsoft" ? "Tài khoản Microsoft" : "Tài khoản offline")
                        : "Thêm ở trang Cài đặt"
                    color: Theme.textMuted; font.pixelSize: 10
                }
            }
        }
    }

    Text {
        id: version
        anchors { left: parent.left; bottom: parent.bottom; margins: 18 }
        text: "v" + Qt.application.version
        color: Theme.textMuted
        font.pixelSize: 10
    }
}
