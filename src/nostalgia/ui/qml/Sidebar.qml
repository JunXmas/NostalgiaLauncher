import QtQuick

/* Thanh bên: hiệu, danh mục, thẻ tài khoản, chân trang. STORE của bản mẫu là CHƠI CHUNG. */
Rectangle {
    id: root
    property int currentIndex: 0
    property string playerName: ""
    property string accountKind: ""

    color: Theme.surface

    // Thanh bên là nơi DUY NHẤT nói cho Theme biết đang ở tab nào — và nó cũng là nơi duy
    // nhất biết điều đó. Đặt ở đây thay vì để từng trang tự khai: trang tự khai thì trang
    // quên khai sẽ mang màu của trang trước, lỗi âm thầm không ai thấy.
    onCurrentIndexChanged: Theme.page = root.currentIndex
    Component.onCompleted: Theme.page = root.currentIndex

    Connections {
        target: Tr
        function onLanguageChanged() { root.entries = root._buildEntries(); }
    }

    property var entries: _buildEntries()
    function _buildEntries() {
        return [
            // `block` là icon chính (dải sprite khối xoay); `glyph` là dự phòng lúc dải
            // chưa sinh xong hoặc sinh hỏng.
            { label: Tr.text("home"),        glyph: "⌂", block: "grass" },
            { label: Tr.text("instances"),   glyph: "⛏", block: "crafting" },
            { label: Tr.text("library"),     glyph: "⚙", block: "bookshelf" },
            { label: Tr.text("accounts"),    glyph: "☺", block: "diamond" },
            { label: Tr.text("multiplayer"), glyph: "⛶", block: "command" },
            { label: Tr.text("log"),         glyph: "≡", block: "chest" },
            { label: Tr.text("settings"),    glyph: "☸", block: "redstone" }
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
                Text { text: "NOSTAL"; color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true; font.letterSpacing: 1.2 }
                // Lục cố định, KHÔNG theo `Theme.accent`: tên sản phẩm là thứ duy nhất trên
                // màn hình không được đổi màu theo tab. Nó cùng màu với chiếc lá ở logo bên
                // trái, và nhận ra được ở mọi trang.
                Text { text: "GIA"; color: Theme.brand; font.pixelSize: Theme.fontTitle; font.bold: true; font.letterSpacing: 1.2 }
            }
            Text {
                text: Tr.text("tagline")
                color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.4
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
                block: modelData.block
                // Màu của mục thứ `index` — cùng một bảng mà `Theme.accent` lấy ra, nên mục
                // được chọn ở thanh bên và cả trang bên phải luôn cùng sắc.
                tint: Theme.accents[index]
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
                width: 38; height: 38; radius: 0
                color: root.playerName ? Theme.accentDeep : Theme.border
                Text {
                    anchors.centerIn: parent
                    text: root.playerName ? root.playerName.charAt(0).toUpperCase() : "?"
                    color: "white"; font.pixelSize: Theme.fontTitle; font.bold: true
                }
            }
            Column {
                spacing: 3
                Text { text: root.playerName ? Tr.text("hello_prefix") : Tr.text("not_signed_in")
                       color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
                Text { text: root.playerName ? root.playerName : "—"
                       color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true }
            }
        }

        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 8 }
            height: 28
            radius: 0
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
                    color: Theme.textMuted; font.pixelSize: Theme.fontLabel
                }
            }
        }
    }

    Row {
        id: footer
        anchors { left: parent.left; bottom: parent.bottom; margins: 20 }
        spacing: 12
        Text { text: "v" + Qt.application.version; color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
    }
}
