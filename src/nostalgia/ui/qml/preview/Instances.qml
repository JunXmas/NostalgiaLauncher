import QtQuick
import QtQuick.Window
import "../" as Legacy

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
    InertialGrid {
        id: instanceGrid
        visible: !root.serverMode
        objectName: "instancesScroll"
        anchors.top: filters.bottom; anchors.topMargin: 24
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
