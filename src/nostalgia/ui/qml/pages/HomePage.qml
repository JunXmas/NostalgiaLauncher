import QtQuick
import QtQuick.Controls
import "../"

/* Trang chủ: khu hero, nút chơi, và danh sách bản chơi THẬT. */
Item {
    id: page
    property bool gameRunning: false
    property string search: ""

    function visibleInstances() {
        if (!page.search) return bridge.instances;
        var needle = page.search.toLowerCase();
        return bridge.instances.filter(function (entry) {
            return entry.label.toLowerCase().indexOf(needle) >= 0
                || entry.versionId.toLowerCase().indexOf(needle) >= 0;
        });
    }

    Connections {
        target: bridge
        function onGameStarted(instanceId) { page.gameRunning = true; }
        function onGameStopped(exitCode) { page.gameRunning = false; }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: body.height + 40
        clip: true

        Column {
            id: body
            width: parent.width
            spacing: 0

            HeroPanel {
                width: parent.width
                height: 300
                instanceCount: bridge.instances.length
                gameRunning: page.gameRunning

                Column {
                    anchors { left: parent.left; bottom: playRow.top; margins: 28; bottomMargin: 20 }
                    spacing: 6
                    Text {
                        text: greeting()
                        color: Theme.textMuted; font.pixelSize: 13
                        function greeting() {
                            var hour = new Date().getHours();
                            if (hour < 11) return "Chào buổi sáng!";
                            if (hour < 18) return "Chào buổi chiều!";
                            return "Chào buổi tối!";
                        }
                    }
                    Text { text: "Hôm nay chơi gì?"; color: Theme.text; font.pixelSize: 32; font.bold: true }
                }

                Row {
                    id: playRow
                    anchors { left: parent.left; bottom: parent.bottom; margins: 28 }
                    spacing: 14

                    PlayButton {
                        playable: bridge.instances.length > 0 && bridge.accounts.length > 0
                                  && !bridge.busy && !page.gameRunning
                        instanceLabel: bridge.instances.length > 0
                                       ? bridge.instances[0].label : "chưa có bản chơi"
                        onClicked: bridge.play(bridge.instances[0].instanceId,
                                               bridge.accounts[0].playerName)
                    }
                }
            }

            Item { width: 1; height: 26 }

            // Hàng công cụ của danh sách
            Item {
                width: parent.width
                height: 40

                Text {
                    anchors { left: parent.left; leftMargin: 28; verticalCenter: parent.verticalCenter }
                    text: "BẢN CHƠI CỦA TÔI"
                    color: Theme.text; font.pixelSize: 14; font.bold: true; font.letterSpacing: 1.2
                }

                Row {
                    anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
                    spacing: 10

                    Rectangle {
                        width: 220; height: 34; radius: Theme.radiusSmall
                        color: Theme.surface
                        border.color: searchField.activeFocus ? Theme.accent : Theme.border
                        border.width: 1
                        Behavior on border.color { ColorAnimation { duration: Theme.quick } }

                        TextInput {
                            id: searchField
                            anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                            verticalAlignment: TextInput.AlignVCenter
                            color: Theme.text
                            font.pixelSize: 12
                            clip: true
                            onTextChanged: page.search = text
                        }
                        Text {
                            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                            visible: searchField.text.length === 0
                            text: "Tìm bản chơi..."
                            color: Theme.textMuted; font.pixelSize: 12
                        }
                    }
                }
            }

            Item { width: 1; height: 16 }

            Text {
                x: 28
                visible: page.visibleInstances().length === 0
                text: bridge.instances.length === 0
                      ? "Chưa có bản chơi nào."
                      : "Không có bản chơi nào khớp \"" + page.search + "\"."
                color: Theme.textMuted; font.pixelSize: 12
            }

            Grid {
                x: 28
                width: parent.width - 56
                columns: Math.max(1, Math.floor(width / 248))
                spacing: Theme.gap

                Repeater {
                    model: page.visibleInstances()
                    InstanceCard {
                        label: modelData.label
                        versionId: modelData.versionId
                    }
                }
            }
        }
    }
}
