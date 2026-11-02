import QtQuick
import QtQuick.Window
import QtQuick.Controls as Controls
import "../" as Legacy
import "ActionReasons.js" as Reasons

Item {
    id: root
    objectName: "minimalInstances"
    property string selectedGroup: ""
    property bool serverMode: false
    readonly property var filtered: bridge.instances.filter(function (i) {
        return (!root.selectedGroup || i.groupName === root.selectedGroup) && (!search.text.trim() || (i.label + " " + i.versionId + " " + i.groupName).toLowerCase().indexOf(search.text.toLowerCase().trim()) >= 0);
    }).sort(function (a, b) {
        return a.favorite !== b.favorite ? (a.favorite ? -1 : 1) : a.label.localeCompare(b.label);
    })
    readonly property var groups: {
        var r = [Legacy.Tr.phrase("Tất cả nhóm")];
        bridge.instances.forEach(function (i) {
            if (i.groupName && r.indexOf(i.groupName) < 0)
                r.push(i.groupName);
        });
        return r;
    }
    Item {
        id: header
        width: parent.width
        height: 86
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Text {
                text: root.serverMode ? Legacy.Tr.phrase("Máy chủ của bạn") : Legacy.Tr.phrase("Bản chơi")
                color: GlassTheme.text
                font.family: GlassTheme.displayFont
                font.pixelSize: GlassTheme.fontPage
                font.weight: Font.DemiBold
            }
            Text {
                text: root.serverMode ? Legacy.Tr.phrase("Cùng xây một thế giới. Theo cách của bạn.") : bridge.instances.length + Legacy.Tr.plural(" thế giới, theo cách của bạn.", bridge.instances.length)
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontBody
            }
        }
        Button {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            objectName: "createModernInstance"
            label: root.serverMode ? Legacy.Tr.phrase("Tạo server  +") : Legacy.Tr.phrase("Tạo bản chơi  +")
            primary: true
            onClicked: { if (root.serverMode && servers.item) servers.item.openCreate(); else create.openDialog(); }
        }
    }
    Row {
        id: workspaceTabs
        anchors.top: header.bottom
        spacing: 8
        Button { objectName: "workspaceInstances"; label: Legacy.Tr.phrase("Bản chơi"); selected: !root.serverMode; quiet: true; onClicked: root.serverMode = false }
        Button { objectName: "workspaceServers"; label: "Server · Pro+"; selected: root.serverMode; quiet: true; onClicked: root.serverMode = true }
    }
    GuideCard {
        id: guide; anchors.top: workspaceTabs.bottom; anchors.topMargin: 8
        width: parent.width; visible: !root.serverMode; topicId: "create"
    }
    Flow {
        id: filters
        anchors.top: guide.bottom
        visible: !root.serverMode
        anchors.topMargin: 8
        width: parent.width
        spacing: 12
        Input {
            id: search
            objectName: "minimalInstanceSearch"
            width: Math.max(200, Math.min(360, root.width - 405))
            height: 42 * GlassTheme.scale
            placeholder: Legacy.Tr.phrase("Tìm bản chơi…")
        }
        Select {
            width: Math.min(190, root.width * 0.23)
            model: root.groups
            onActivated: function (index) {
                root.selectedGroup = index ? root.groups[index] : "";
            }
        }
        Button {
            objectName: "openImportDialog"
            label: Legacy.Tr.phrase("Nhập bản chơi")
            quiet: true
            onClicked: imports.openDialog()
        }
        Button {
            objectName: "openBackupDialog"
            label: Legacy.Tr.phrase("Xuất modpack")
            quiet: true
            Accessible.name: Legacy.Tr.phrase("Đóng gói modpack thành MRPACK hoặc ZIP")
            onClicked: manager.openDialog()
        }
    }
    ActionHint {
        id: playHint
        objectName: "instancePlayHint"
        width: parent.width; anchors.top: filters.bottom; anchors.topMargin: 12
        visible: !root.serverMode && !!reason && bridge.instances.length > 0
        reason: Legacy.Tr.phrase(Reasons.playing(bridge))
    }
    InertialGrid {
        id: instanceGrid
        visible: !root.serverMode
        objectName: "instancesScroll"
        anchors.top: playHint.bottom; anchors.topMargin: playHint.visible ? 12 : 0
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        readonly property bool compact: GlassTheme.preferences && GlassTheme.preferences.compactUi
        readonly property int columns: compact ? 1 : Math.max(1, Math.floor((width + 8) / (270 * GlassTheme.scale)))
        cellWidth: Math.max(1, Math.floor((width - 8) / columns))
        cellHeight: (compact ? 92 : 204) * GlassTheme.scale + 16
        model: root.filtered
        delegate: Item {
            required property var modelData
            width: instanceGrid.cellWidth; height: instanceGrid.cellHeight
            InstanceTile {
                width: parent.width - 16; height: parent.height - 16
                compact: instanceGrid.compact; entry: parent.modelData
                onEditRequested: function(entry) { editor.openFor(entry); }
            }
        }
        footer: Item {
            width: instanceGrid.width - 8; height: root.filtered.length ? 16 : empty.implicitHeight + 32
            PaymentText {
                id: empty
                visible: !root.filtered.length; width: parent.width
                text: bridge.instances.length ? Legacy.Tr.phrase("Không có bản chơi phù hợp.") : Legacy.Tr.phrase("Tạo bản chơi đầu tiên của bạn để bắt đầu.")
                color: GlassTheme.muted
            }
        }
    }
    Loader {
        id: servers
        objectName: "serversPageLoader"
        anchors.top: workspaceTabs.bottom; anchors.topMargin: 18
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        active: root.serverMode; visible: active; source: "Servers.qml"
    }
    function isPackUrl(url) {
        var lower = String(url).toLowerCase();
        return lower.endsWith(".mrpack") || lower.endsWith(".zip");
    }
    // Chỉ nhập MỘT modpack mỗi lần thả: hai việc nhập song song giẫm nhau. Trả số file modpack thấy.
    function importDropped(urls) {
        var packs = [];
        for (var index = 0; index < urls.length; index++)
            if (root.isPackUrl(urls[index])) packs.push(String(urls[index]));
        if (packs.length > 0) contentBridge.importModpackFile(packs[0], "", "");
        return packs.length;
    }
    DropArea {
        id: dropZone
        objectName: "packDropArea"
        anchors.fill: parent
        // Popup đang mở thì overlay của nó nhận cú kéo; DropArea nằm dưới sẽ nuốt cú thả .jar của LocalModBridge.
        enabled: !root.serverMode && !(Controls.Overlay.overlay && Controls.Overlay.overlay.visibleChildren.length > 0)
        z: 50
        // `urls` chỉ có trên sự kiện kéo, không có trên `DropArea.drag`, nên tự giữ trạng thái.
        property bool holdingPack: false
        onEntered: function (drag) {
            dropZone.holdingPack = !!drag.urls && drag.urls.some(root.isPackUrl);
            if (!dropZone.holdingPack) drag.accepted = false;
        }
        onExited: dropZone.holdingPack = false
        onDropped: function (drop) {
            dropZone.holdingPack = false;
            if (root.importDropped(drop.urls) > 0) drop.accept();
        }
        Rectangle {
            objectName: "packDropOverlay"
            anchors.fill: parent
            visible: dropZone.holdingPack
            radius: 22
            color: GlassTheme.alpha(GlassTheme.background, 0.94)
            border.color: GlassTheme.accent; border.width: 2
            Column {
                anchors.centerIn: parent; spacing: 10
                PaymentText { anchors.horizontalCenter: parent.horizontalCenter; text: Legacy.Tr.phrase("Thả để nhập modpack"); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontPage; font.weight: Font.DemiBold }
                PaymentText { anchors.horizontalCenter: parent.horizontalCenter; text: Legacy.Tr.phrase(".mrpack (Modrinth) hoặc .zip (CurseForge) — tạo thành một bản chơi mới"); color: GlassTheme.muted }
            }
        }
    }
    ModRepairDialog { id: repair }
    ModernCreateInstanceDialog {
        id: create
        objectName: "modernCreateDialog"
    }
    InstanceManager {
        id: editor
        onRepairRequested: function(instance) { repair.openFor(instance); }
        onExportRequested: function(instance) { manager.openDialog(instance.instanceId); }
    }
    ImportDialog {
        id: imports
    }
    BackupDialog {
        id: manager
    }
}
