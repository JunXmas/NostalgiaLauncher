import QtQuick
import "../" as Legacy

// Bấm Chơi: chọn thế giới (Singleplayer) hoặc server (Multiplayer) để vào thẳng, như chọn video.
// Cầu nối đọc đĩa ở luồng nền rồi phát `playChoicesReady`; bản chơi không có gì để chọn (hoặc
// bản game không vào thẳng được) thì mở game luôn như trước, không hiện cửa sổ.
WorkspaceDialog {
    id: root
    objectName: "playChoiceDialog"
    property string instanceId: ""
    property var worlds: []
    property var servers: []
    property int tab: 0
    property int sortIndex: 0
    readonly property var instance: bridge.instances.find(function (i) { return i.instanceId === root.instanceId; }) || ({})
    readonly property string gameVersion: /^(fabric-loader|quilt-loader)-/.test(instance.versionId || "") ? (instance.versionId || "").split("-").pop() : (instance.versionId || "").split("-")[0]
    readonly property var gameTypes: [Legacy.Tr.phrase("Sinh tồn"), Legacy.Tr.phrase("Sáng tạo"), Legacy.Tr.phrase("Phiêu lưu"), Legacy.Tr.phrase("Khán giả")]
    readonly property var shown: {
        var query = search.text.trim().toLowerCase();
        var rows = (root.tab === 0 ? root.worlds : root.servers).filter(function (row) {
            var haystack = root.tab === 0 ? row.worldName + " " + row.worldFolder : row.serverName + " " + row.address;
            return !query || haystack.toLowerCase().indexOf(query) >= 0;
        });
        if (root.sortIndex === 1)
            rows.sort(function (a, b) { return (a.worldName || a.serverName).localeCompare(b.worldName || b.serverName); });
        return rows;
    }
    title: Legacy.Tr.phrase("Chơi") + " · " + (instance.label || instanceId)
    description: Legacy.Tr.phrase("Chọn nơi để vào thẳng, hoặc chỉ mở game.")
    preferredWidth: 1060 * GlassTheme.scale
    preferredHeight: 780 * GlassTheme.scale
    Connections {
        target: bridge
        function onPlayChoicesReady(instanceId, worlds, servers, firstTab) {
            if (!worlds.length && !servers.length) {
                bridge.play(instanceId);
                return;
            }
            root.instanceId = instanceId;
            root.worlds = worlds;
            root.servers = servers;
            root.tab = firstTab === "multiplayer" ? 1 : 0;
            root.sortIndex = 0;
            search.text = "";
            root.open();
        }
    }
    function justPlay() {
        root.close();
        bridge.play(root.instanceId);
    }
    VersionArtwork { id: keyArt; visible: false; gameVersion: root.gameVersion }
    Item {
        anchors.fill: parent
        Row {
            id: controls
            width: parent.width
            spacing: 12
            MotionTabs {
                width: 290 * GlassTheme.scale
                objectName: "playChoiceTabs"
                namePrefix: "playChoiceTab-"
                labels: [Legacy.Tr.phrase("Chơi đơn") + "  " + root.worlds.length, Legacy.Tr.phrase("Chơi mạng") + "  " + root.servers.length]
                currentIndex: root.tab
                onSelected: function (index) { root.tab = index; grid.contentY = grid.originY; }
            }
            Input {
                id: search
                objectName: "playChoiceSearch"
                width: parent.width - x - sort.width - parent.spacing
                placeholder: Legacy.Tr.phrase("Tìm theo tên…")
            }
            Select {
                id: sort
                objectName: "playChoiceSort"
                width: 170 * GlassTheme.scale
                model: [Legacy.Tr.phrase("Gần đây"), Legacy.Tr.phrase("Tên A–Z")]
                currentIndex: root.sortIndex
                onActivated: function (index) { root.sortIndex = index; }
            }
        }
        InertialGrid {
            id: grid
            objectName: "playChoiceGrid"
            anchors.top: controls.bottom; anchors.topMargin: 18
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            readonly property int columns: Math.max(1, Math.floor((width + 8) / (230 * GlassTheme.scale)))
            cellWidth: Math.max(1, Math.floor((width - 8) / columns))
            cellHeight: Math.round((cellWidth - 16) * 9 / 16) + 82 * GlassTheme.scale
            model: root.shown
            delegate: Item {
                required property var modelData
                width: grid.cellWidth; height: grid.cellHeight
                PlayChoiceTile {
                    objectName: root.tab === 0 ? "playWorld-" + parent.modelData.worldFolder : "playServer-" + parent.modelData.address
                    width: parent.width - 16; height: parent.height - 16
                    imageUrl: parent.modelData.iconUrl
                    fallbackUrl: keyArt.artSource
                    title: root.tab === 0 ? parent.modelData.worldName : parent.modelData.serverName
                    subtitle: root.tab === 0 ? (root.gameTypes[parent.modelData.gameType] || root.gameTypes[0]) + " · " + Legacy.Tr.message(parent.modelData.lastPlayedText) : parent.modelData.address
                    badges: root.tab !== 0 ? [] : [parent.modelData.hardcore ? {label: Legacy.Tr.phrase("Hardcore"), danger: true} : null, parent.modelData.cheats ? {label: Legacy.Tr.phrase("Cheat"), danger: false} : null].filter(Boolean)
                    onChosen: {
                        var row = parent.modelData;
                        root.close();
                        if (root.tab === 0) bridge.playWorld(root.instanceId, row.worldFolder);
                        else bridge.playServer(root.instanceId, row.address);
                    }
                }
            }
            footer: Item {
                width: grid.width - 8; height: root.shown.length ? 16 : empty.implicitHeight + 32
                PaymentText {
                    id: empty
                    objectName: "playChoiceEmpty"
                    visible: !root.shown.length; width: parent.width
                    text: search.text.trim() ? Legacy.Tr.phrase("Không có kết quả phù hợp.") : root.tab === 0 ? Legacy.Tr.phrase("Bản chơi này chưa có thế giới nào. Tạo world mới trong game.") : Legacy.Tr.phrase("Chưa thêm server nào. Thêm server trong game ở mục Multiplayer.")
                    color: GlassTheme.muted
                }
            }
        }
    }
    footer: Row {
        spacing: 10
        // Game tự có màn tạo world: mở game là xong, launcher không tự dựng world.
        Button { objectName: "playChoiceNew"; visible: root.tab === 0; label: Legacy.Tr.phrase("+ Tạo world mới"); quiet: true; onClicked: root.justPlay() }
        Button { objectName: "playChoiceJustPlay"; label: Legacy.Tr.phrase("Chỉ mở game"); primary: true; onClicked: root.justPlay() }
    }
}
