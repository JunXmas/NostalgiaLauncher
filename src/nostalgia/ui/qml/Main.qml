import QtQuick

/* Gốc là `Item` chứ không phải `Window`.

   Lý do rất thực tế: `QQuickView` chụp được nội dung ra PNG mà không cần màn hình, nên tôi
   soi được giao diện bằng mắt ở từng bước thay vì đoán. Kích thước và tiêu đề cửa sổ do
   `app.py` đặt. */
Item {
    id: window
    implicitWidth: 1360
    implicitHeight: 860

    Rectangle { anchors.fill: parent; color: Theme.background }

    Sidebar {
        id: sidebar
        objectName: "sidebar"
        width: 232
        anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
        playerName: bridge.activePlayerName
        accountKind: {
            var chosen = bridge.accounts.find(function (account) { return account.playerName === bridge.activePlayerName; });
            return chosen ? chosen.accountKind : "";
        }
    }

    // Đổi trang bằng mờ dần chứ không nhảy phắt: mắt bám được chỗ mình vừa bấm.
    Item {
        id: content
        anchors { top: parent.top; bottom: parent.bottom; left: sidebar.right; right: parent.right }

        Loader {
            id: pageLoader
            objectName: "pageLoader"
            anchors.fill: parent
            source: content.pageFor(sidebar.currentIndex)
            opacity: 0
            onLoaded: fadeIn.restart()

            // Thẻ trên hero bấm được: chúng đổi trang y như bấm ở thanh bên.
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
            case 2: return "pages/ModsPage.qml";
            case 4: return "pages/ResourcesPage.qml";
            default: return "pages/PlaceholderPage.qml";
            }
        }
    }

    // Dải báo lỗi: trượt xuống từ trên, tự biến mất. Lỗi im lặng là lỗi tệ nhất.
    Rectangle {
        id: banner
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
            font.pixelSize: 12
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

    SignInDialog { anchors.fill: parent }
}
