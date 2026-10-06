import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "minimalHome"
    signal navigate(int index)
    property string chosenId: ""
    property var instances: bridge.instances
    // Refresh after the bridge invalidates its cached rows, regardless of signal order.
    Timer {
        id: refresh
        interval: 0
        onTriggered: root.instances = bridge.instances
    }
    Connections {
        target: bridge
        function onInstancesChanged() {
            refresh.restart();
        }
    }
    readonly property var orderedInstances: root.instances.slice().sort(function (a, b) {
        var recent = (b.lastPlayedAt || 0) - (a.lastPlayedAt || 0);
        if (recent)
            return recent;
        if (a.favorite !== b.favorite)
            return a.favorite ? -1 : 1;
        return a.label.localeCompare(b.label);
    })
    readonly property var chosen: root.instances.find(function (i) {
        return i.instanceId === root.chosenId;
    }) || root.orderedInstances[0] || null
    readonly property var featured: root.orderedInstances.slice(0, 3)
    InertialScroll {
        objectName: "homeScroll"
        anchors.fill: parent
        contentHeight: body.height + 32
        Column {
            id: body
            width: parent.width - 8
            spacing: 28
            Row {
                width: parent.width
                height: 68
                spacing: 12
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Text {
                        text: "Không gian của bạn"
                        color: GlassTheme.muted
                        font.family: GlassTheme.font
                        font.pixelSize: 13
                    }
                    Text {
                        text: "Chào " + (bridge.activePlayerName || "bạn") + "."
                        color: GlassTheme.text
                        font.family: GlassTheme.font
                        font.pixelSize: 30
                        font.weight: Font.DemiBold
                        font.letterSpacing: -0.7
                    }
                }
            }
            Glass {
                id: hero
                width: parent.width
                height: Math.max(310, 280 * GlassTheme.scale)
                radius: 26
                padding: 32
                color: "#ad17322a"
                Column {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 165
                    spacing: 18
                    Text {
                        text: root.chosen ? "SẴN SÀNG KHI BẠN MUỐN" : "MỘT KHỞI ĐẦU MỚI"
                        color: GlassTheme.accent
                        font.family: GlassTheme.font
                        font.pixelSize: 10
                        font.letterSpacing: 1.6
                    }
                    Text {
                        width: parent.width
                        text: root.chosen ? "Tiếp tục cuộc
phiêu lưu của bạn." : "Thế giới tiếp theo
đang chờ bạn."
                        color: GlassTheme.text
                        font.family: GlassTheme.font
                        font.pixelSize: root.width < 750 ? 32 : 40
                        font.weight: Font.DemiBold
                        font.letterSpacing: -1.1
                        lineHeight: 1.13
                    }
                    Text {
                        width: parent.width
                        elide: Text.ElideRight
                        text: root.chosen ? root.chosen.label + "  ·  " + root.chosen.versionId : "Tạo một bản chơi hoặc khám phá modpack trong thư viện."
                        color: GlassTheme.muted
                        font.family: GlassTheme.font
                        font.pixelSize: 13
                    }
                    Row {
                        spacing: 12
                        Button {
                            objectName: "minimalPlay"
                            width: 155
                            height: 46
                            primary: true
                            label: bridge.gameRunning ? "Dừng game" : root.chosen ? "Chơi ngay  →" : "Tạo bản chơi  +"
                            clickable: bridge.gameRunning || (!bridge.busy && !bridge.storageBusy && (!root.chosen || !!bridge.activePlayerName))
                            onClicked: bridge.gameRunning ? bridge.stopGame() : root.chosen ? bridge.play(root.chosen.instanceId) : root.navigate(1)
                        }
                        Button {
                            height: 46
                            label: "Khám phá modpack"
                            quiet: true
                            onClicked: root.navigate(2)
                        }
                    }
                }
                Legacy.BlockIcon {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.rightMargin: 10
                    width: root.width < 750 ? 112 : 148
                    height: width
                    block: "grass"
                    glyph: ""
                    spinning: false
                    opacity: 0.95
                }
            }
            Item {
                width: parent.width
                height: 34
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Bản chơi của bạn"
                    color: GlassTheme.text
                    font.family: GlassTheme.font
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                }
                Button {
                    anchors.right: parent.right
                    height: 34
                    label: "Xem tất cả  →"
                    quiet: true
                    onClicked: root.navigate(1)
                }
            }
            Grid {
                width: parent.width
                columns: Math.max(1, Math.min(3, Math.floor((width + 16) / 250)))
                spacing: 16
                Repeater {
                    model: root.featured
                    InstanceTile {
                        width: (parent.width - (parent.columns - 1) * 16) / parent.columns
                        entry: modelData
                        pickOnly: true
                        selected: root.chosen && root.chosen.instanceId === entry.instanceId
                        onPicked: root.chosenId = entry.instanceId
                    }
                }
            }
            Text {
                visible: !root.instances.length
                text: "Bản chơi bạn tạo sẽ xuất hiện tại đây."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: 13
            }
            Rectangle {
                width: parent.width
                height: 1
                color: "#13ffffff"
            }
            Item {
                width: parent.width
                height: 64
                Column {
                    spacing: 8
                    Text {
                        text: "Một chút mới mẻ cho thế giới quen thuộc."
                        color: GlassTheme.text
                        font.family: GlassTheme.font
                        font.pixelSize: 15
                    }
                    Text {
                        text: "Mod, shader và modpack — tìm điều hợp với bạn."
                        color: GlassTheme.muted
                        font.family: GlassTheme.font
                        font.pixelSize: 13
                    }
                }
                Button {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    label: "Mở thư viện  →"
                    onClicked: root.navigate(2)
                }
            }
        }
    }
}
