import QtQuick
import "../"

/*
  Trang chủ: ảnh làng phủ kín vùng nội dung; mọi thứ khác là tấm kính nổi trên ảnh — lời chào
  và pill trạng thái ở góc trên trái, cột thông tin bên phải, dải bản chơi dưới cùng, và sáu
  thẻ neo vào công trình trong ảnh. Nút CHƠI đứng giữa khoảng trống trước dải bản chơi.
*/
Item {
    id: page
    objectName: "homePage"
    property string search: ""
    // Mặc định là bản vừa chơi gần nhất, không phải mục đầu bảng chữ cái. Đây là một
    // binding: `onPicked` gán đè sẽ phá nó, nên lựa chọn tay của người dùng được giữ
    // nguyên trong phiên.
    property int chosenIndex: page.lastPlayedIndex()
    signal navigate(int pageIndex)
    signal navigateToLibrary(string contentKind)

    readonly property var chosen: bridge.instances.length > 0
                                  ? bridge.instances[Math.min(chosenIndex, bridge.instances.length - 1)] : null
    readonly property int rightColumnWidth: page.width < 900 ? 240 : 296
    readonly property int instanceStripHeight: 78 + 168 + Theme.pad

    function visibleInstances() {
        if (!page.search) return bridge.instances;
        var needle = page.search.toLowerCase();
        return bridge.instances.filter(function (entry) {
            return entry.label.toLowerCase().indexOf(needle) >= 0
                || entry.versionId.toLowerCase().indexOf(needle) >= 0;
        });
    }
    /* Chỉ số instance có `lastPlayedAt` lớn nhất; chưa ai chơi lần nào thì mục đầu. */
    function lastPlayedIndex() {
        var best = 0;
        var bestPlayedAt = 0;
        for (var index = 0; index < bridge.instances.length; index++) {
            var playedAt = bridge.instances[index].lastPlayedAt || 0;
            if (playedAt > bestPlayedAt) {
                bestPlayedAt = playedAt;
                best = index;
            }
        }
        return best;
    }
    function playChosen() {
        if (page.chosen && bridge.activePlayerName) bridge.play(page.chosen.instanceId);
    }

    // ----- ảnh nền phủ kín, tối dần về đáy để chữ và kính nổi rõ -----
    // Ảnh 2528 px, luôn bị thu nhỏ: mipmap để Qt lọc đúng khi thu (không mipmap là lấy mẫu
    // 2×2 → răng cưa và "mờ nhoè" trên sao và cạnh khối).
    Image {
        id: photo
        anchors.fill: parent
        source: "../assets/hero.jpg"
        fillMode: Image.PreserveAspectCrop
        smooth: true; mipmap: true
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.00; color: "#26000000" }
            GradientStop { position: 0.55; color: "#33000000" }
            GradientStop { position: 1.00; color: "#c0080c09" }
        }
    }

    HeroPanel {
        anchors.fill: parent
        photo: photo
        instanceCount: bridge.instances.length
        reservedRight: page.rightColumnWidth + Theme.gap * 2
        onNavigate: function (pageIndex) { page.navigate(pageIndex); }
        onNavigateToLibrary: function (contentKind) { page.navigateToLibrary(contentKind); }
    }

    /* ----- góc trên trái: lời chào -----

       Chữ đặt thẳng lên ảnh sao thì không đọc được, dù có đổ bóng: nền phía sau lúc sáng lúc
       tối tuỳ chỗ. minecraft.net xử đúng chuyện này — chữ hero của họ nằm trên một hộp đặc
       mờ, góc vuông, tràn hẳn ra mép trái. Làm theo: hộp bám mép trái màn hình. */
    Rectangle {
        id: greetingBox
        anchors { left: parent.left; top: parent.top; topMargin: 18 }
        width: greetingText.width + 52
        height: greetingText.height + 34
        color: "#d40b100d"

        // Vạch xanh dọc mép trái — cùng dấu hiệu với tiêu đề thẻ ở Panel.qml.
        Rectangle {
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            width: 3
            color: Theme.accent
        }
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 1
            color: "#1cffffff"
        }

        Column {
            id: greetingText
            anchors { left: parent.left; leftMargin: 28; verticalCenter: parent.verticalCenter }
            spacing: 4

            Text {
                text: greeting()
                color: Theme.accent
                font.family: Theme.pixel
                font.pixelSize: Theme.fontLabel
                font.letterSpacing: Theme.trackLabel
                function greeting() {
                    var hour = new Date().getHours();
                    if (hour < 11) return "CHÀO BUỔI SÁNG";
                    if (hour < 18) return "CHÀO BUỔI CHIỀU";
                    return "CHÀO BUỔI TỐI";
                }
            }
            Text {
                text: "HÔM NAY CHƠI GÌ?"
                color: Theme.text
                font.family: Theme.pixel
                font.pixelSize: Theme.fontHero
                font.letterSpacing: 1
            }
            Text {
                text: bridge.instances.length > 0 ? "Tiếp tục cuộc phiêu lưu của bạn."
                                                  : "Tạo một bản chơi để bắt đầu."
                color: Theme.textMuted
                font.pixelSize: Theme.fontBody
            }
        }
    }
    Row {
        anchors { right: rightColumn.left; top: parent.top; margins: Theme.gap; topMargin: 22 }
        spacing: 10
        StatusPill { glyph: "▣"; text: bridge.instances.length + " bản chơi"; translucent: true }
        StatusPill {
            dotColor: bridge.gameRunning ? Theme.accent : Theme.textMuted
            pulsing: bridge.gameRunning
            text: bridge.gameRunning ? "Đang chơi" : "Sẵn sàng"
            translucent: true
        }
    }

    // ----- nút CHƠI: giữa vùng trái, ngay trên dải bản chơi -----
    PlayButton {
        anchors { bottom: instanceStrip.top; bottomMargin: 22 }
        x: Math.round((rightColumn.x - width) / 2)
        playable: page.chosen !== null && bridge.activePlayerName.length > 0 && !bridge.busy && !bridge.gameRunning
        running: bridge.gameRunning
        instances: bridge.instances
        chosenIndex: page.chosenIndex
        onClicked: page.playChosen()
        onStopRequested: bridge.stopGame()
        onPicked: function (index) { page.chosenIndex = index; }
        onCreateRequested: page.navigate(1)
    }

    // ----- cột phải: kính nổi trên ảnh -----
    Column {
        id: rightColumn
        width: page.rightColumnWidth
        anchors { top: parent.top; right: parent.right; margins: Theme.gap; topMargin: 76 }
        spacing: Theme.gap

        ProfileCard {
            id: profileCard
            objectName: "profileCard"
            width: parent.width
            height: implicitHeight
            Behavior on height { NumberAnimation { duration: Theme.quick } }
            translucent: true
            accounts: bridge.accounts
            activePlayerName: bridge.activePlayerName
            onAddAccountRequested: function (name) { if (name) bridge.addOfflineAccount(name); }
            onMicrosoftSignInRequested: bridge.signInMicrosoft()
            onAccountChosen: function (name) { bridge.setActiveAccount(name); }
            onRemoveRequested: function (name) { bridge.removeAccount(name); }
        }
        ContinueCard {
            objectName: "continueCard"
            width: parent.width
            height: Math.min(340, page.height - 380)
            translucent: true
            worlds: bridge.recentWorlds
            servers: bridge.recentServers
            playable: bridge.activePlayerName.length > 0 && !bridge.busy && !bridge.gameRunning
            onWorldChosen: function (instanceId, worldFolder) { bridge.playWorld(instanceId, worldFolder); }
            onServerChosen: function (instanceId, address) { bridge.playServer(instanceId, address); }
        }
        FriendsCard {
            width: parent.width
            height: 132
            translucent: true
            onOpenMultiplayer: page.navigate(4)
        }
    }

    // ----- dải bản chơi dưới cùng: một hàng, cuộn ngang khi nhiều -----
    Panel {
        id: instanceStrip
        translucent: true
        anchors { left: parent.left; right: rightColumn.left; bottom: parent.bottom; margins: Theme.gap }
        height: page.instanceStripHeight

        Item {
            anchors.fill: parent
            Text {
                id: listTitle
                anchors { left: parent.left; top: parent.top }
                text: "BẢN CHƠI CỦA TÔI"
                color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true; font.letterSpacing: 1.2
            }
            Row {
                anchors { right: parent.right; top: parent.top; topMargin: -4 }
                spacing: 9
                TextField { width: 200; placeholder: "Tìm bản chơi..."; onTextChanged: page.search = text }
                ActionButton { label: "+  Tạo mới"; onClicked: page.navigate(1) }
            }
            Text {
                anchors { left: parent.left; top: listTitle.bottom; topMargin: 22 }
                visible: page.visibleInstances().length === 0
                text: bridge.instances.length === 0 ? "Chưa có bản chơi nào."
                                                    : "Không có bản chơi nào khớp \"" + page.search + "\"."
                color: Theme.textMuted; font.pixelSize: Theme.fontBody
            }
            ListView {
                id: strip
                anchors { left: parent.left; right: parent.right; top: listTitle.bottom; topMargin: 20; bottom: parent.bottom }
                orientation: ListView.Horizontal
                clip: true
                spacing: Theme.gap
                model: page.visibleInstances()
                delegate: InstanceCard {
                    width: 230; height: 168
                    label: modelData.label
                    versionId: modelData.versionId
                    playtimeText: modelData.playtimeText; launchCount: modelData.launchCount
                    worldCount: modelData.worldCount; modCount: modelData.modCount
                    playable: bridge.activePlayerName.length > 0 && !bridge.busy && !bridge.gameRunning
                    onPlayRequested: bridge.play(modelData.instanceId)
                }
            }
        }
    }
}
