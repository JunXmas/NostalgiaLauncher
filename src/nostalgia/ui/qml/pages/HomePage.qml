import QtQuick
import "../"

/*
  Trang chủ: ảnh làng phủ kín vùng nội dung, mọi thứ khác nổi trên ảnh — lời chào góc trên
  trái, khối CHƠI ở giữa, cột CHƠI TIẾP + BẠN BÈ bên phải, dải bản chơi dưới cùng.

  KHÔNG còn sáu thẻ neo vào công trình trong ảnh. Chúng dẫn tới đúng những trang mà thanh bên
  đã dẫn tới, nên người dùng có hai đường đi khác hình dạng cho cùng một đích — và trên ảnh
  sao thì chúng che mất chính thứ làm trang chủ đẹp. Thanh bên là đường duy nhất để chuyển
  trang; trang chủ chỉ còn việc của riêng nó là CHƠI.

  Ô HỒ SƠ cũng bỏ: thanh bên đã có thẻ tài khoản ở chân, và trang TÀI KHOẢN làm việc đó đầy
  đủ hơn. Cần đăng nhập thì khối CHƠI nói ngay tại chỗ.
*/
Item {
    id: page
    objectName: "homePage"
    property string search: ""
    // Main ghi vào (Binding có `when`): thanh bên thu gọn thì sáu mục của nó hiện thành
    // thẻ neo vào các hành tinh trong ảnh hero — xem PlanetNav.qml.
    property bool sidebarCollapsed: false
    // Mặc định là bản vừa chơi gần nhất, không phải mục đầu bảng chữ cái. Đây là một
    // binding: `onPicked` gán đè sẽ phá nó, nên lựa chọn tay của người dùng được giữ
    // nguyên trong phiên.
    property int chosenIndex: page.lastPlayedIndex()
    signal navigate(int pageIndex)

    readonly property var chosen: bridge.instances.length > 0
                                  ? bridge.instances[Math.min(chosenIndex, bridge.instances.length - 1)] : null
    readonly property int rightColumnWidth: page.width < 900 ? 240 : 296
    readonly property int instanceStripHeight: 78 + 178 + Theme.pad

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
    /* Thứ còn thiếu để bấm CHƠI được. Tài khoản trước bản chơi: tạo bản chơi xong mà chưa
       đăng nhập thì vẫn chưa chơi được, nên hỏi cái chặn trước. */
    readonly property string missingKind: bridge.activePlayerName.length === 0 ? "account"
                                        : bridge.instances.length === 0 ? "instance" : ""

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
    /* Lớp phủ đậm hơn hẳn bản cũ (#26/#33/#c0).

       Ảnh dải ngân hà có nhiễu sao khắp khung, nên chữ trắng đặt lên bất kỳ đâu cũng có chỗ
       tương phản kém. Đậm hơn là đổi ảnh từ "hình chính" thành "phông nền", và đó đúng là
       vai trò của nó — thứ phải đọc được là chữ, không phải từng ngôi sao. */
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.00; color: "#73101520" }
            GradientStop { position: 0.55; color: "#8c0e121b" }
            GradientStop { position: 1.00; color: "#e60c1017" }
        }
    }

    /* ----- thẻ hành tinh: chỉ khi thanh bên thu gọn -----

       Bản 1.0.x có sáu thẻ này thường trực và bị bỏ ở 1.0.14 vì trùng đường đi với thanh
       bên. Nay chúng là MẶT KIA của cùng đồng xu: thanh bên thu gọn còn cột icon thì sáu
       mục của nó bay ra từ các hành tinh — không lúc nào có hai đường cùng hình dạng.
       Nằm trên ảnh + lớp phủ, dưới các panel nghiệp vụ (khối CHƠI, cột phải, dải bản chơi). */
    PlanetNav {
        objectName: "planetNav"
        anchors.fill: parent
        visible: page.sidebarCollapsed
        reservedRight: rightColumn.width + Theme.gap * 2
        onNavigate: function (pageIndex) { page.navigate(pageIndex); }
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

    // ----- khối CHƠI: giữa vùng trái, ngay trên dải bản chơi -----
    PlayButton {
        objectName: "playBlock"
        anchors { bottom: instanceStrip.top; bottomMargin: 22 }
        x: Math.round((rightColumn.x - width) / 2)
        playable: page.chosen !== null && bridge.activePlayerName.length > 0 && !bridge.busy && !bridge.gameRunning
        running: bridge.gameRunning
        instances: bridge.instances
        chosenIndex: page.chosenIndex
        missingKind: page.missingKind
        onClicked: page.playChosen()
        onStopRequested: bridge.stopGame()
        onPicked: function (index) { page.chosenIndex = index; }
        onCreateRequested: page.navigate(1)
        onAddAccountRequested: page.navigate(3)
    }

    // ----- cột phải: kính nổi trên ảnh -----
    Column {
        id: rightColumn
        width: page.rightColumnWidth
        anchors { top: parent.top; right: parent.right; margins: Theme.gap; topMargin: 76 }
        spacing: Theme.gap

        ContinueCard {
            objectName: "continueCard"
            width: parent.width
            height: Math.min(340, page.height - 260)
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
                    width: 230; height: 178
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
