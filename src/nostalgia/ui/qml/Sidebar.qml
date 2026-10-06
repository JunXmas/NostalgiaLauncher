import QtQuick

/* Thanh bên: hiệu, danh mục, thẻ tài khoản, chân trang. STORE của bản mẫu là CHƠI CHUNG. */
Rectangle {
    id: root
    property int currentIndex: 0
    property string playerName: ""
    property string accountKind: ""
    // Đường dẫn file skin của tài khoản đang dùng; rỗng = chưa tải xong, lúc đó vẽ chữ cái đầu.
    property string skinFile: ""
    /* Thu gọn: chỉ còn cột icon. Ở trang chủ, sáu mục điều hướng khi đó hiện thành thẻ neo
       vào các hành tinh trong ảnh hero (PlanetNav) — thu gọn không phải là mất đường đi,
       mà là đổi thanh bên lấy bầu trời. Trạng thái sống theo phiên, không ghi đĩa. */
    property bool collapsed: false

    clip: true
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
            { label: Tr.text("log"),         glyph: "≡", block: "barrel" },
            { label: Tr.text("settings"),    glyph: "☸", block: "redstone" }
        ];
    }

    Row {
        id: brand
        anchors { top: parent.top; left: parent.left; margins: root.collapsed ? 14 : 20 }
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
            visible: !root.collapsed
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

    Flickable {
        id: navigationScroll
        objectName: "navigationScroll"
        anchors { top: brand.bottom; bottom: accountCard.top; topMargin: 20; bottomMargin: 12;
                  left: parent.left; right: parent.right; margins: 12 }
        clip: true
        contentWidth: width
        contentHeight: navigationItems.height
        boundsBehavior: Flickable.StopAtBounds
        Column {
        id: navigationItems
        width: parent.width
        spacing: Theme.compactUi ? 0 : 4

        Repeater {
            model: root.entries
            NavItem {
                label: modelData.label
                glyph: modelData.glyph
                block: modelData.block
                compact: root.collapsed
                // Màu của mục thứ `index` — cùng một bảng mà `Theme.accent` lấy ra, nên mục
                // được chọn ở thanh bên và cả trang bên phải luôn cùng sắc.
                tint: Theme.accents[index]
                selected: index === root.currentIndex
                onClicked: { if (index !== root.currentIndex) notifier.playUi("nav"); root.currentIndex = index; }
            }
        }

        /* Discord cộng đồng: LIÊN KẾT RA NGOÀI, không phải điểm đến.

           Nằm dưới vạch ngăn, tách khỏi bảy mục trên nó — bảy mục kia đổi trang bên phải,
           ô này mở trình duyệt rồi người dùng vẫn đứng nguyên ở trang cũ. Hai loại hành vi
           khác nhau thì phải nhìn ra được trước khi bấm, nên không sáng lên (`selected` luôn
           false), không đụng `currentIndex`, không đụng `Theme.page`.

           Màu `textMuted` chứ không màu thương hiệu Discord: bảng màu ở đây là của Nostalgia,
           và một ô tím lạ giữa thanh bên sẽ đọc thành "mục quan trọng nhất" — sai hẳn cấp bậc.
           Cùng lý do và cùng cách với `collapseToggle` ngay dưới. */
        /* Vạch ngăn: hiện ở CẢ HAI chế độ. Thu gọn mà giấu vạch đi thì ở cột icon, cái
           phong bì nằm sát ngay dưới bảy khối và đọc thành mục thứ tám — đúng thứ vạch này
           sinh ra để chặn. Ôm trong một Item cao hơn để vạch có khoảng thở: nhịp 4 px của
           Column là nhịp giữa các mục cùng loại, không phải nhịp giữa hai nhóm. */
        Item {
            width: parent.width
            height: 15
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width; height: 1
                color: Theme.border
            }
        }

        NavItem {
            objectName: "communityLink"
            accessibleLabel: Tr.text("community")
            label: root.collapsed ? "" : Tr.text("community")
            /* Logo Discord thật (assets/discord.png), không phải chữ "✉" như trước: phong bì
               là "thư", không ai đọc ra Discord, mà đây đúng là chỗ cần nhận ra NGAY bằng
               hình. Không có khối Minecraft nào nói được điều này nên nó đi đường `image`.
               Giữ màu lam chính hiệu của Discord — logo đổi màu thì mất tác dụng nhận diện,
               đó là lý do duy nhất một thứ ở thanh bên được nằm ngoài bảng màu Nostalgia. */
            image: "assets/discord.png"
            glyph: "✉"  // dự phòng, nếu ảnh thiếu trong gói
            compact: root.collapsed
            tint: Theme.textMuted
            // Qua cầu nối chứ không `Qt.openUrlExternally` thẳng trong QML: URL phải sống ở
            // `repo/endpoints.py` cạnh mọi địa chỉ khác, để đổi lời
            // mời chỉ sửa một dòng và test kiểm được — chuỗi ghi cứng trong QML thì không.
            onClicked: settingsBridge.openCommunityPage()
        }

        /* Ủng hộ: cùng nhóm "không phải điểm đến" với CỘNG ĐỒNG ở trên, nên nằm cùng phía
           dưới vạch ngăn và cũng không đụng `currentIndex`.

           Ở thanh bên chứ không chỉ ở cuối trang CÀI ĐẶT: thanh bên hiện ở MỌI trang, còn nút
           dưới trang CÀI ĐẶT phải bấm hai lớp mới tới — một lời mời mà không ai thấy thì bằng
           không có. Vẫn là một ô nằm im: không tự bật, không chặn gì.

           Màu vàng `warning` chứ không `textMuted` như hai ô cạnh nó: đây là ô duy nhất ở đây
           cần nhìn ra được, và vàng là màu nhạt nhất trong bảng mà không trùng bảy màu tab —
           không ô nào khác dùng nó nên nó không đọc thành "tab thứ tám". */
        NavItem {
            objectName: "donateLink"
            accessibleLabel: Tr.text("donate")
            label: root.collapsed ? "" : Tr.text("donate")
            // Khối beacon: trong game nó là thứ người chơi dựng được sau khi hạ boss rồi đặt
            // lên một bệ quặng quý — ngọn sáng bắn thẳng lên trời. Đúng nghĩa ở đây, và nó
            // nằm cùng ngôn ngữ với bảy khối phía trên thay vì một ký tự lạc font.
            block: "beacon"
            glyph: "♥"  // chỉ dùng mấy nhịp đầu, lúc dải sprite chưa sinh xong
            compact: root.collapsed
            tint: Theme.warning
            // Mở hộp QR, không ra trình duyệt: `donateDialog` là thuộc tính ngữ cảnh đặt ở
            // `ui/app.py`, phủ cả thanh bên nên gọi được từ đây.
            onClicked: donateDialog.open()
        }

        // Nút thu gọn/mở rộng, cùng hàng lối với các mục trên nó.
        NavItem {
            objectName: "collapseToggle"
            label: root.collapsed ? "" : Tr.text("collapse_sidebar")
            glyph: root.collapsed ? "»" : "«"
            compact: root.collapsed
            tint: Theme.textMuted
            onClicked: root.collapsed = !root.collapsed
        }
    }

    }

    // Thẻ tài khoản. Chưa đăng nhập thì nói thẳng là chưa, không vẽ người giả.
    // Thu gọn thì chỉ còn ô avatar — tên và loại tài khoản không nhét vừa cột icon.
    Rectangle {
        id: accountCard
        anchors { left: parent.left; right: parent.right; bottom: footer.top; margins: root.collapsed ? 8 : 14; bottomMargin: 16 }
        height: root.collapsed ? 54 : 96
        radius: Theme.radiusSmall
        color: Theme.surfaceHigh

        Row {
            anchors { top: parent.top; left: parent.left; margins: 12 }
            spacing: 10
            /* Đầu nhân vật cắt từ chính file skin, như trang TÀI KHOẢN.
               Chữ cái đầu chỉ là dự phòng: skin tải nền nên vài nhịp đầu `skinFile` còn rỗng,
               và tài khoản ngoại tuyến chưa chọn skin thì cũng không có file. */
            Rectangle {
                objectName: "sidebarAvatar"
                width: 38; height: 38; radius: Theme.modern ? 8 : 0
                color: root.playerName ? Theme.accentDeep : Theme.border
                Text {
                    anchors.centerIn: parent
                    visible: root.skinFile.length === 0
                    text: root.playerName ? root.playerName.charAt(0).toUpperCase() : "?"
                    color: "white"; font.pixelSize: Theme.fontTitle; font.bold: true
                }
                SkinFace {
                    objectName: "sidebarSkinFace"
                    anchors.centerIn: parent
                    visible: root.skinFile.length > 0
                    size: 32
                    source: root.skinFile
                }
            }
            Column {
                visible: !root.collapsed
                spacing: 3
                Text { text: root.playerName ? Tr.text("hello_prefix") : Tr.text("not_signed_in")
                       color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
                Text { text: root.playerName ? root.playerName : "—"
                       color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true }
            }
        }

        Rectangle {
            visible: !root.collapsed
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 8 }
            height: 28
            radius: Theme.modern ? 8 : 0
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
        visible: !root.collapsed
        anchors { left: parent.left; bottom: parent.bottom; margins: 20 }
        spacing: 12
        Text { text: "v" + Qt.application.version; color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
    }
}
