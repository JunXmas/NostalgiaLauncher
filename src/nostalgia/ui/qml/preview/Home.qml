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
                        text: Legacy.Tr.phrase("Hôm nay, mình chơi gì?")
                        color: GlassTheme.muted
                        font.family: GlassTheme.font
                        font.pixelSize: GlassTheme.fontBody
                    }
                    Text {
                        text: Legacy.Tr.phrase("Chào ") + (bridge.activePlayerName || Legacy.Tr.phrase("bạn")) + "."
                        color: GlassTheme.text
                        font.family: GlassTheme.displayFont
                        font.pixelSize: GlassTheme.fontPage
                        font.weight: Font.DemiBold
                        font.letterSpacing: -0.7
                    }
                }
            }
            HomeHero {
                width: parent.width
                chosen: root.chosen
                onPlayRequested: bridge.gameRunning ? bridge.stopGame() : root.chosen ? bridge.play(root.chosen.instanceId) : root.navigate(1)
                onLibraryRequested: root.navigate(2)
            }
            GuideCard { width: parent.width; topicId: "start" }
            Item {
                width: parent.width
                height: 34
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Legacy.Tr.phrase("Bản chơi của bạn")
                    color: GlassTheme.text
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontSection
                    font.weight: Font.DemiBold
                }
                Button {
                    anchors.right: parent.right
                    height: 34
                    label: Legacy.Tr.phrase("Xem tất cả  →")
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
                text: Legacy.Tr.phrase("Bản chơi bạn tạo sẽ xuất hiện tại đây.")
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontBody
            }
            HomeExplore {
                width: parent.width
                onNavigate: function (index) {
                    root.navigate(index);
                }
            }
        }
    }
}
