import QtQuick
import "../"

/*
  Trang chủ: ảnh làng phủ kín vùng nội dung; mọi thứ khác là tấm kính nổi trên ảnh — lời chào
  và pill trạng thái ở góc trên trái, cột thông tin bên phải, dải bản chơi dưới cùng, và sáu
  thẻ neo vào công trình trong ảnh. Nút CHƠI đứng giữa khoảng trống trước dải bản chơi.
*/
Item {
    id: page
    property bool gameRunning: false
    property string search: ""
    property int chosenIndex: 0
    signal navigate(int pageIndex)

    readonly property var chosen: bridge.instances.length > 0
                                  ? bridge.instances[Math.min(chosenIndex, bridge.instances.length - 1)] : null
    readonly property int rightColumnWidth: 296
    readonly property int instanceStripHeight: 78 + 168 + Theme.pad

    function visibleInstances() {
        if (!page.search) return bridge.instances;
        var needle = page.search.toLowerCase();
        return bridge.instances.filter(function (entry) {
            return entry.label.toLowerCase().indexOf(needle) >= 0
                || entry.versionId.toLowerCase().indexOf(needle) >= 0;
        });
    }
    function playChosen() {
        if (page.chosen && bridge.activePlayerName) bridge.play(page.chosen.instanceId);
    }

    Connections {
        target: bridge
        function onGameStarted(instanceId) { page.gameRunning = true; }
        function onGameStopped(exitCode) { page.gameRunning = false; }
    }

    // ----- ảnh nền phủ kín, tối dần về đáy để chữ và kính nổi rõ -----
    Image {
        id: photo
        anchors.fill: parent
        source: "../assets/hero.jpg"
        fillMode: Image.PreserveAspectCrop
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
        onNavigate: function (pageIndex) { page.navigate(pageIndex); }
    }

    // ----- góc trên trái: lời chào; góc trên phải của vùng giữa: hai pill -----
    Column {
        anchors { left: parent.left; top: parent.top; margins: Theme.gap; leftMargin: 28; topMargin: 22 }
        spacing: 3
        Text {
            text: greeting(); color: Theme.text; font.pixelSize: 13; style: Text.Raised; styleColor: "#80000000"
            function greeting() {
                var hour = new Date().getHours();
                if (hour < 11) return "Chào buổi sáng!";
                if (hour < 18) return "Chào buổi chiều!";
                return "Chào buổi tối!";
            }
        }
        Text { text: "Hôm nay chơi gì?"; color: Theme.text; font.pixelSize: 26; font.bold: true
               style: Text.Raised; styleColor: "#80000000" }
        Text {
            text: bridge.instances.length > 0 ? "Tiếp tục cuộc phiêu lưu của bạn." : "Tạo một bản chơi để bắt đầu."
            color: Theme.accent; font.pixelSize: 13; style: Text.Raised; styleColor: "#80000000"
        }
    }
    Row {
        anchors { right: rightColumn.left; top: parent.top; margins: Theme.gap; topMargin: 22 }
        spacing: 10
        StatusPill { glyph: "▣"; text: bridge.instances.length + " bản chơi"; translucent: true }
        StatusPill {
            dotColor: page.gameRunning ? Theme.accent : Theme.textMuted
            pulsing: page.gameRunning
            text: page.gameRunning ? "Đang chơi" : "Sẵn sàng"
            translucent: true
        }
    }

    // ----- nút CHƠI: giữa vùng trái, ngay trên dải bản chơi -----
    PlayButton {
        anchors { bottom: instanceStrip.top; bottomMargin: 22 }
        x: Math.round((rightColumn.x - width) / 2)
        playable: page.chosen !== null && bridge.activePlayerName.length > 0 && !bridge.busy && !page.gameRunning
        instances: bridge.instances
        chosenIndex: page.chosenIndex
        onClicked: page.playChosen()
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
            width: parent.width
            height: 150 + Math.max(1, bridge.accounts.length) * 48
            translucent: true
            accounts: bridge.accounts
            activePlayerName: bridge.activePlayerName
            onAddAccountRequested: function (name) { if (name) bridge.addOfflineAccount(name); }
            onMicrosoftSignInRequested: bridge.signInMicrosoft()
            onAccountChosen: function (name) { bridge.setActiveAccount(name); }
            onRemoveRequested: function (name) { bridge.removeAccount(name); }
        }
        VersionsCard {
            width: parent.width
            height: 214
            translucent: true
            versions: bridge.installedVersions
            busy: bridge.busy
            onInstallRequested: function (versionId) { if (versionId) bridge.installVersion(versionId); }
        }
        FriendsCard {
            width: parent.width
            height: 132
            translucent: true
            onOpenMultiplayer: page.navigate(5)
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
                color: Theme.text; font.pixelSize: 14; font.bold: true; font.letterSpacing: 1.2
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
                color: Theme.textMuted; font.pixelSize: 12
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
                    playable: bridge.activePlayerName.length > 0 && !bridge.busy && !page.gameRunning
                    onPlayRequested: bridge.play(modelData.instanceId)
                }
            }
        }
    }

    // Thanh tiến độ khi đang tải: mỏng, nằm dưới cùng, không che gì.
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: bridge.busy ? 30 : 0
        color: Theme.surfaceHigh
        clip: true
        Behavior on height { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        Text {
            anchors { left: parent.left; leftMargin: 18; verticalCenter: parent.verticalCenter }
            text: bridge.progressText
            color: Theme.textMuted; font.pixelSize: 11
        }
        Rectangle {
            anchors { left: parent.left; bottom: parent.bottom }
            height: 2
            width: parent.width * bridge.progressFraction
            color: Theme.accent
            Behavior on width { NumberAnimation { duration: Theme.quick } }
        }
    }
}
