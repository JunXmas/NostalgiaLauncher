import QtQuick

/* Gốc là `Item` chứ không phải `Window`.

   Lý do rất thực tế: `QQuickView` chụp được nội dung ra PNG mà không cần màn hình, nên tôi
   soi được giao diện bằng mắt ở từng bước thay vì đoán. Kích thước và tiêu đề cửa sổ do
   `app.py` đặt. */
Item {
    id: window
    implicitWidth: 1360
    implicitHeight: 860
    /* Nền pha một chút màu của tab đang mở, và chuyển màu chứ không nhảy.

       Chỉ 6% — đủ để cả khung hình nghiêng về sắc của tab, chưa đủ để thành một nền có màu
       (nền màu mạnh làm chữ và thẻ mất tương phản). `Behavior` ở đây chứ không ở `Theme.qml`:
       Theme là singleton readonly, ràng buộc trong đó không gắn Behavior được — và đằng nào
       cũng chỉ có một chỗ vẽ nền. */
    Rectangle {
        anchors.fill: parent
        color: Theme.mix(Theme.background, Theme.accent, 0.06)
        Behavior on color { ColorAnimation { duration: Theme.slow; easing.type: Easing.OutCubic } }
    }

    Sidebar {
        id: sidebar
        objectName: "sidebar"
        // Thu gọn còn cột icon 64 px; nội dung trượt theo chứ không nhảy.
        width: collapsed ? 64 : (window.width < 1100 ? 190 : 232)
        Behavior on width { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
        playerName: bridge.activePlayerName
        // Lấy từ `accountBridge` chứ không `bridge`: hàng ở đây có kèm `skinFile`, và nó tự
        // dựng lại khi skin tải xong (`skinsChanged`) — tra hai nơi thì đầu và loại tài khoản
        // sẽ lệch nhịp nhau.
        readonly property var activeAccount: accountBridge.accounts.find(function (account) {
            return account.accountId === bridge.activeAccountId;
        }) || null
        accountKind: activeAccount ? activeAccount.accountKind : ""
        skinFile: activeAccount ? activeAccount.skinFile : ""
    }

    // Đổi trang bằng mờ dần chứ không nhảy phắt: mắt bám được chỗ mình vừa bấm.
    Item {
        id: content
        anchors { top: parent.top; bottom: parent.bottom; left: sidebar.right; right: parent.right }

        // Bản mới phải thấy được ở mọi trang, không phải đi tìm trong CÀI ĐẶT.
        UpdateBanner {
            id: updateBanner
            anchors { top: parent.top; left: parent.left; right: parent.right }
        }

        Loader {
            id: pageLoader
            objectName: "pageLoader"
            anchors { top: updateBanner.bottom; bottom: parent.bottom; left: parent.left; right: parent.right }
            source: content.pageFor(sidebar.currentIndex)
            opacity: 0
            onLoaded: fadeIn.restart()

            // Trang chủ cần biết thanh bên đang thu gọn để bày các thẻ hành tinh.
            // Binding một chiều từ đây thay vì trang tự với sang sidebar: trang không
            // được biết sidebar tồn tại (các trang khác không có property này).
            Binding {
                target: pageLoader.item
                property: "sidebarCollapsed"
                value: sidebar.collapsed
                when: pageLoader.item !== null && pageLoader.item.hasOwnProperty("sidebarCollapsed")
            }

            // Khối "còn thiếu" ở trang chủ đổi trang y như bấm ở thanh bên.
            Connections {
                target: pageLoader.item
                ignoreUnknownSignals: true
                function onNavigate(pageIndex) { sidebar.currentIndex = pageIndex; }
            }

            NumberAnimation on opacity {
                id: fadeIn
                from: 0; to: 1
                duration: Theme.normal
                easing.type: Easing.OutCubic
                running: false
            }
        }

        function pageFor(index) {
            switch (index) {
            case 0: return "pages/HomePage.qml";
            case 1: return "pages/InstancesPage.qml";
            case 2: return "pages/LibraryPage.qml";
            case 3: return "pages/AccountsPage.qml";
            case 4: return "pages/MultiplayerPage.qml";
            case 5: return "pages/LogPage.qml";
            case 6: return "pages/SettingsPage.qml";
            default: return "pages/PlaceholderPage.qml";
            }
        }
    }

    // Dải báo lỗi: trượt xuống từ trên, tự biến mất. Lỗi im lặng là lỗi tệ nhất.
    Rectangle {
        id: banner
        objectName: "errorBanner"
        property string message: ""
        anchors { top: parent.top; right: parent.right; margins: 18 }
        width: Math.min(460, window.width - sidebar.width - 60)
        height: message ? 52 : 0
        radius: Theme.radiusSmall
        color: Theme.danger
        clip: true
        opacity: message ? 1 : 0
        Behavior on height { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.normal } }

        Text {
            anchors { fill: parent; margins: 14 }
            text: banner.message
            color: "white"
            font.pixelSize: Theme.fontBody
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        Timer { id: hideBanner; interval: 6000; onTriggered: banner.message = "" }
    }

    Connections {
        target: bridge
        function onFailed(message) { banner.message = message; hideBanner.restart(); }
    }
    Connections {
        target: contentBridge
        function onFailed(message) { banner.message = message; hideBanner.restart(); }
    }
    Connections {
        target: catalogBridge
        function onFailed(message) { banner.message = message; hideBanner.restart(); }
    }
    // Hộp thoại Nhập bản chơi là đường chọn file duy nhất còn lại, nên lỗi của nó cũng phải
    // lên dải này: `failed` cho hỏng lúc chạy nền, `importError` cho từ chối ngay tại chỗ.
    Connections {
        target: importBridge
        function onFailed(message) { banner.message = message; hideBanner.restart(); }
        function onImportError(message) { banner.message = message; hideBanner.restart(); }
    }

    LoadingToast { id: loadingToast; z: 90 }
    NotificationToast { z: 91; bottomOffset: loadingToast.active ? loadingToast.height + Theme.gap * 2 : Theme.gap }
    SignInDialog { anchors.fill: parent }
    // Hộp hỏi lại dùng chung của mọi trang (app.py lộ nó qua context property `confirmDialog`).
    ConfirmDialog { objectName: "confirmDialog"; anchors.fill: parent }
}
