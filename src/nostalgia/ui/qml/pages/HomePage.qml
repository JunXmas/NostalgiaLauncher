import QtQuick
import "../"

/* Trang chủ: hai cột như bản mẫu — giữa là hero + danh sách bản chơi, phải là các ô thông tin. */
Item {
    id: page
    property bool gameRunning: false
    property string search: ""
    signal navigate(int pageIndex)

    readonly property var chosen: bridge.instances.length > 0 ? bridge.instances[0] : null

    function visibleInstances() {
        if (!page.search) return bridge.instances;
        var needle = page.search.toLowerCase();
        return bridge.instances.filter(function (entry) {
            return entry.label.toLowerCase().indexOf(needle) >= 0
                || entry.versionId.toLowerCase().indexOf(needle) >= 0;
        });
    }

    function playChosen() {
        if (page.chosen && bridge.accounts.length > 0)
            bridge.play(page.chosen.instanceId, bridge.accounts[0].playerName);
    }

    Connections {
        target: bridge
        function onGameStarted(instanceId) { page.gameRunning = true; }
        function onGameStopped(exitCode) { page.gameRunning = false; }
    }

    // ----- cột phải -----
    Column {
        id: rightColumn
        width: 296
        anchors { top: parent.top; right: parent.right; bottom: parent.bottom; margins: Theme.gap }
        spacing: Theme.gap

        ProfileCard {
            width: parent.width
            height: bridge.accounts.length > 0 ? 150 : 190
            playerName: bridge.accounts.length > 0 ? bridge.accounts[0].playerName : ""
            accountKind: bridge.accounts.length > 0 ? bridge.accounts[0].accountKind : ""
            playerUuid: bridge.accounts.length > 0 ? bridge.accounts[0].playerUuid : ""
            onAddAccountRequested: function (name) { if (name) bridge.addOfflineAccount(name); }
        }
        VersionsCard {
            width: parent.width
            height: 214
            versions: bridge.installedVersions
            busy: bridge.busy
            onInstallRequested: function (versionId) { if (versionId) bridge.installVersion(versionId); }
        }
        FriendsCard {
            width: parent.width
            height: 132
            onOpenMultiplayer: page.navigate(5)
        }
    }

    // ----- cột giữa -----
    Flickable {
        anchors { top: parent.top; bottom: parent.bottom; left: parent.left; right: rightColumn.left }
        contentHeight: middle.height + 28
        clip: true

        Column {
            id: middle
            width: parent.width
            spacing: Theme.gap
            topPadding: Theme.gap

            HeroPanel {
                width: parent.width - Theme.gap * 2
                x: Theme.gap
                height: 404
                instanceCount: bridge.instances.length
                gameRunning: page.gameRunning
                onNavigate: function (pageIndex) { page.navigate(pageIndex); }

                Column {
                    anchors { left: parent.left; top: parent.top; margins: 22 }
                    spacing: 4
                    Text {
                        text: greeting(); color: Theme.textMuted; font.pixelSize: 12
                        function greeting() {
                            var hour = new Date().getHours();
                            if (hour < 11) return "Chào buổi sáng!";
                            if (hour < 18) return "Chào buổi chiều!";
                            return "Chào buổi tối!";
                        }
                    }
                    Text { text: "Hôm nay chơi gì?"; color: Theme.text; font.pixelSize: 26; font.bold: true }
                    Text {
                        text: bridge.instances.length > 0
                              ? "Tiếp tục cuộc phiêu lưu của bạn."
                              : "Tạo một bản chơi để bắt đầu."
                        color: Theme.accent; font.pixelSize: 12
                    }
                }

                PlayButton {
                    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 20 }
                    playable: page.chosen !== null && bridge.accounts.length > 0
                              && !bridge.busy && !page.gameRunning
                    instanceLabel: page.chosen ? page.chosen.label : "chưa có bản chơi"
                    versionId: page.chosen ? page.chosen.versionId : ""
                    onClicked: page.playChosen()
                    onPickRequested: page.navigate(1)
                }
            }

            // ----- ô danh sách bản chơi -----
            Panel {
                width: parent.width - Theme.gap * 2
                x: Theme.gap
                // Chiều cao đủ ôm trọn lưới: phần đầu, cộng số hàng nhân chiều cao thẻ.
                readonly property int rows: Math.ceil(
                    Math.max(1, page.visibleInstances().length) / Math.max(1, grid.columns))
                height: 78 + rows * 186 + (rows - 1) * Theme.gap + Theme.pad

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
                        TextField {
                            width: 200
                            placeholder: "Tìm bản chơi..."
                            onTextChanged: page.search = text
                        }
                        ActionButton {
                            label: "+  Tạo mới"
                            onClicked: page.navigate(1)
                        }
                    }

                    Text {
                        anchors { left: parent.left; top: listTitle.bottom; topMargin: 22 }
                        visible: page.visibleInstances().length === 0
                        text: bridge.instances.length === 0
                              ? "Chưa có bản chơi nào."
                              : "Không có bản chơi nào khớp \"" + page.search + "\"."
                        color: Theme.textMuted; font.pixelSize: 12
                    }

                    Grid {
                        id: grid
                        anchors { left: parent.left; right: parent.right; top: listTitle.bottom; topMargin: 20 }
                        columns: Math.max(1, Math.floor(width / (230 + Theme.gap)))
                        spacing: Theme.gap

                        Repeater {
                            model: page.visibleInstances()
                            InstanceCard {
                                label: modelData.label
                                versionId: modelData.versionId
                                playable: bridge.accounts.length > 0 && !bridge.busy && !page.gameRunning
                                onPlayRequested: {
                                    if (bridge.accounts.length > 0)
                                        bridge.play(modelData.instanceId, bridge.accounts[0].playerName);
                                }
                            }
                        }
                    }
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
