import QtQuick

Item {
    id: root
    property var entry: ({})
    signal editRequested(var entry)
    implicitHeight: body.height
    Column {
        id: body
        width: parent.width; spacing: 8
        InstanceCard {
            visible: !Theme.compactUi
            width: parent.width; height: 198 + (Theme.textScale - 1) * 80
            label: root.entry.label || root.entry.instanceId || ""
            versionId: root.entry.versionId || ""
            iconUrl: root.entry.iconUrl || ""
            playtimeText: root.entry.playtimeText || ""
            launchCount: root.entry.launchCount || 0
            worldCount: root.entry.worldCount || 0; modCount: root.entry.modCount || 0
            customGameDir: root.entry.customGameDir || false
            showPlay: false
            playable: bridge.activePlayerName.length > 0 && !bridge.busy
            onPlayRequested: bridge.play(root.entry.instanceId)
        }
        Text {
            visible: Theme.compactUi
            width: parent.width; elide: Text.ElideRight
            text: (root.entry.label || root.entry.instanceId) + " · " + root.entry.versionId
            color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true
        }
        Text {
            width: parent.width; elide: Text.ElideRight
            text: root.entry.groupName || Tr.phrase("Chưa phân nhóm")
            color: Theme.textMuted; font.pixelSize: Theme.fontLabel
        }
        Flow {
            width: parent.width; spacing: 8
            ActionButton { label: Tr.phrase("Chơi"); clickable: bridge.activePlayerName.length > 0 && !bridge.busy && !storageBridge.busy; onClicked: bridge.play(root.entry.instanceId) }
            ActionButton { primary: false; label: Tr.phrase("Quản lý"); onClicked: root.editRequested(root.entry) }
            ActionButton { primary: false; label: root.entry.favorite ? "★" : "☆"; Accessible.name: Tr.phrase("Ghim bản chơi"); onClicked: storageBridge.setOrganization(root.entry.instanceId, root.entry.groupName || "", !root.entry.favorite) }
        }
        Rectangle { visible: Theme.compactUi; width: parent.width; height: 1; color: Theme.border }
    }
}
