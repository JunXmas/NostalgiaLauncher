import QtQuick

/* Thanh bên: hiệu, danh mục, thẻ tài khoản, chân trang. STORE của bản mẫu là CHƠI CHUNG. */
Rectangle {
    id: root
    property int currentIndex: 0
    property string playerName: ""
    property string accountKind: ""

    color: Theme.surface

    Connections {
        target: Tr
        function onLanguageChanged() { root.entries = root._buildEntries(); }
    }

    property var entries: _buildEntries()
    function _buildEntries() {
        return [
            { label: Tr.text("home"),        glyph: "⌂" },
            { label: Tr.text("instances"),   glyph: "⛏" },
            { label: Tr.text("library"),     glyph: "⚙" },
            { label: Tr.text("accounts"),    glyph: "☺" },
            { label: Tr.text("multiplayer"), glyph: "⛶" },
            { label: Tr.text("log"),         glyph: "≡" },
            { label: Tr.text("settings"),    glyph: "☸" }
        ];
    }

    Row {
        id: brand
        anchors { top: parent.top; left: parent.left; margins: 20 }
        spacing: 11

        // Logo khối lá Minecraft của jun (packaging/icons/nostalgia-source.png → assets/logo.png),
        // cũng là icon ứng dụng.
        Image {
            width: 36; height: 36
            anchors.verticalCenter: parent.verticalCenter
            source: "assets/logo.png"
            sourceSize: Qt.size(68, 68); smooth: true; mipmap: true
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Row {
                Text { text: "NOSTAL"; color: Theme.text; font.pixelSize: 17; font.bold: true; font.letterSpacing: 1.2 }
                Text { text: "GIA"; color: Theme.accent; font.pixelSize: 17; font.bold: true; font.letterSpacing: 1.2 }
            }
            Text {
                text: Tr.text("tagline")
                color: Theme.textMuted; font.pixelSize: 8; font.letterSpacing: 1.4
            }
        }
    }

    Column {
        anchors { top: brand.bottom; topMargin: 24; left: parent.left; right: parent.right; margins: 12 }
        spacing: 4

        Repeater {
            model: root.entries
            NavItem {
                label: modelData.label
                glyph: modelData.glyph
                selected: index === root.currentIndex
                onClicked: { if (index !== root.currentIndex) notifier.playUi("nav"); root.currentIndex = index; }
            }
        }
    }

    // Thẻ tài khoản. Chưa đăng nhập thì nói thẳng là chưa, không vẽ người giả.
    Rectangle {
        id: accountCard
        anchors { left: parent.left; right: parent.right; bottom: footer.top; margins: 14; bottomMargin: 16 }
        height: 96
        radius: Theme.radiusSmall
        color: Theme.surfaceHigh

        Row {
            anchors { top: parent.top; left: parent.left; margins: 12 }
            spacing: 10
            Rectangle {
                width: 38; height: 38; radius: 7
                color: root.playerName ? Theme.accentDeep : Theme.border
                Text {
                    anchors.centerIn: parent
                    text: root.playerName ? root.playerName.charAt(0).toUpperCase() : "?"
                    color: "white"; font.pixelSize: 17; font.bold: true
                }
            }
            Column {
                spacing: 3
                Text { text: root.playerName ? Tr.text("hello_prefix") : Tr.text("not_signed_in")
                       color: Theme.textMuted; font.pixelSize: 10 }
                Text { text: root.playerName ? root.playerName : "—"
                       color: Theme.text; font.pixelSize: 14; font.bold: true }
            }
        }

        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 8 }
            height: 28
            radius: 6
            color: Theme.surface
            Row {
                anchors { left: parent.left; leftMargin: 9; verticalCenter: parent.verticalCenter }
                spacing: 7
                Rectangle {
                    width: 7; height: 7; radius: 3.5
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.playerName ? Theme.accent : Theme.textMuted
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: !root.playerName ? Tr.text("add_on_right")
                          : root.accountKind === "microsoft" ? Tr.text("account_microsoft")
                          : root.accountKind === "ely" ? Tr.text("account_ely") : Tr.text("account_offline")
                    color: Theme.textMuted; font.pixelSize: 10
                }
            }
        }
    }

    Row {
        id: footer
        anchors { left: parent.left; bottom: parent.bottom; margins: 20 }
        spacing: 12
        Text { text: "v" + Qt.application.version; color: Theme.textMuted; font.pixelSize: 10 }
    }
}
