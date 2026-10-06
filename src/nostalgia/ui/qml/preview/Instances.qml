import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "minimalInstances"
    property string selectedGroup: ""
    readonly property var filtered: bridge.instances.filter(function (i) {
        return (!root.selectedGroup || i.groupName === root.selectedGroup) && (!search.text.trim() || (i.label + " " + i.versionId + " " + i.groupName).toLowerCase().indexOf(search.text.toLowerCase().trim()) >= 0);
    }).sort(function (a, b) {
        return a.favorite !== b.favorite ? (a.favorite ? -1 : 1) : a.label.localeCompare(b.label);
    })
    readonly property var groups: {
        var r = ["Tất cả nhóm"];
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
                text: "Bản chơi"
                color: GlassTheme.text
                font.family: GlassTheme.font
                font.pixelSize: 30
                font.weight: Font.DemiBold
            }
            Text {
                text: bridge.instances.length + " thế giới, theo cách của bạn."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: 13
            }
        }
        Button {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            label: "Tạo bản chơi  +"
            primary: true
            onClicked: create.openDialog()
        }
    }
    Row {
        id: filters
        anchors.top: header.bottom
        anchors.topMargin: 8
        width: parent.width
        spacing: 12
        Input {
            id: search
            objectName: "minimalInstanceSearch"
            width: Math.max(200, Math.min(360, root.width - 405))
            height: 42 * GlassTheme.scale
            placeholder: "Tìm bản chơi…"
        }
        Select {
            width: Math.min(190, root.width * 0.23)
            model: root.groups
            onActivated: function (index) {
                root.selectedGroup = index ? root.groups[index] : "";
            }
        }
        Button {
            label: "Nhập bản chơi"
            quiet: true
            onClicked: imports.openDialog()
        }
        Button {
            label: "···"
            width: 36
            quiet: true
            Accessible.name: "Sao lưu và thùng rác"
            onClicked: manager.openDialog()
        }
    }
    InertialScroll {
        objectName: "instancesScroll"
        anchors.top: filters.bottom
        anchors.topMargin: 24
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        contentHeight: grid.height + 32
        Grid {
            id: grid
            width: parent.width - 8
            columns: GlassTheme.preferences && GlassTheme.preferences.compactUi ? 1 : Math.max(1, Math.floor((width + 16) / (270 * GlassTheme.scale)))
            spacing: 16
            Repeater {
                model: root.filtered
                InstanceTile {
                    width: (grid.width - (grid.columns - 1) * 16) / grid.columns
                    compact: GlassTheme.preferences && GlassTheme.preferences.compactUi
                    entry: modelData
                    onEditRequested: function (entry) {
                        editor.openFor(entry);
                    }
                }
            }
            Text {
                visible: !root.filtered.length
                width: grid.width
                text: bridge.instances.length ? "Không có bản chơi phù hợp." : "Tạo bản chơi đầu tiên của bạn để bắt đầu."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: 15
            }
        }
    }
    Legacy.CreateInstanceDialog {
        id: create
        anchors.fill: parent
    }
    Legacy.InstanceEditDialog {
        id: editor
        anchors.fill: parent
    }
    Legacy.ImportInstanceDialog {
        id: imports
        anchors.fill: parent
    }
    Legacy.DataManager {
        id: manager
        anchors.fill: parent
    }
}
