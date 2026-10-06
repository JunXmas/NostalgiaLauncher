import QtQuick
import QtQuick.Controls as Controls

Controls.Popup {
    id: root
    objectName: "modernLibraryFilters"
    parent: Controls.Overlay.overlay
    width: Math.min(680, parent ? parent.width - 40 : 680)
    height: Math.min(600, parent ? parent.height - 40 : 600)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24; modal: true; dim: true; focus: true
    property string kind: "mod"
    signal applied
    onOpened: if (!catalogBridge.releasedVersions.length) catalogBridge.loadReleasedVersions()
    onClosed: applied()
    background: Glass { padding: 0 }
    Controls.Overlay.modal: Rectangle { color: "#aa080b12" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: GlassTheme.quick } }
    contentItem: Item {
        PaymentText { id: heading; width: parent.width - 40; text: "Bộ lọc thư viện"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold }
        Button { anchors.right: parent.right; width: 38; label: "×"; quiet: true; Accessible.name: "Đóng bộ lọc"; onClicked: root.close() }
        Button { id: done; anchors.right: parent.right; anchors.bottom: parent.bottom; label: "Xong"; primary: true; onClicked: root.close() }
        InertialScroll {
            anchors.top: heading.bottom; anchors.topMargin: 24; anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: done.top; anchors.bottomMargin: 18
            contentHeight: contents.implicitHeight + 8
            Column {
                id: contents
                width: parent.width - 8; spacing: 16
                PaymentText { visible: root.kind !== "modpack"; text: "Bản chơi đích"; font.weight: Font.DemiBold }
                Select {
                    visible: root.kind !== "modpack"
                    width: parent.width
                    model: ["Chưa chọn bản chơi"].concat(bridge.instances.map(function(entry) { return entry.label; }))
                    currentIndex: bridge.instances.findIndex(function(entry) { return entry.instanceId === contentBridge.instanceId; }) + 1
                    onActivated: function(index) { contentBridge.selectInstance(index ? bridge.instances[index - 1].instanceId : ""); }
                }
                PaymentText { visible: root.kind === "mod"; text: "Mod loader"; font.weight: Font.DemiBold }
                Flow {
                    visible: root.kind === "mod"
                    width: parent.width; spacing: 8
                    Repeater {
                        model: ["fabric", "forge", "neoforge", "quilt"]
                        Button {
                            label: modelData === "neoforge" ? "NeoForge" : modelData[0].toUpperCase() + modelData.slice(1)
                            selected: contentBridge.selectedLoaders.indexOf(modelData) >= 0
                            onClicked: contentBridge.setLoaderSelected(modelData, !selected)
                        }
                    }
                    Button { label: "Mọi loader"; quiet: true; onClicked: contentBridge.clearLoaders() }
                }
                PaymentText { text: "Phiên bản Minecraft"; font.weight: Font.DemiBold }
                Select {
                    objectName: "libraryGameFilter"
                    width: parent.width
                    model: ["Thêm phiên bản…"].concat(catalogBridge.releasedVersions.map(function(entry) { return entry.versionId; }))
                    onActivated: function(index) {
                        if (index) contentBridge.setGameVersionSelected(catalogBridge.releasedVersions[index - 1].versionId, true);
                        currentIndex = 0;
                    }
                }
                Flow {
                    width: parent.width; spacing: 8
                    Repeater { model: contentBridge.selectedGameVersions; Button { label: modelData + "  ×"; selected: true; onClicked: contentBridge.setGameVersionSelected(modelData, false) } }
                    Button { label: "Mọi phiên bản"; quiet: true; onClicked: contentBridge.clearGameVersions() }
                }
                PaymentText { width: parent.width; text: catalogBridge.busy ? "Đang lấy danh mục Minecraft…" : "Bạn có thể chọn nhiều phiên bản. Đóng cửa sổ để tìm lại với bộ lọc đã chọn."; color: GlassTheme.muted }
            }
        }
    }
}
