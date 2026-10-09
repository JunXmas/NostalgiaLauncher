import QtQuick
import QtQuick.Controls as Controls

Controls.Popup {
    id: root
    objectName: "instanceLibraryDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(1120, parent ? parent.width - 40 : 1120)
    height: Math.min(820, parent ? parent.height - 40 : 820)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24; modal: true; dim: true; focus: true; z: 100
    property var instance: ({})
    property string initialKind: "mod"
    property bool ownsBrowseTarget: false
    readonly property bool installing: projectBridge.installing || (contentBridge.busy && !contentBridge.searching)
    closePolicy: installing ? Controls.Popup.NoAutoClose : Controls.Popup.CloseOnEscape
    function openFor(instance, kind) {
        if (contentBridge.busy || projectBridge.installing || !contentBridge.pinBrowseTarget(instance.instanceId)) return;
        root.instance = instance;
        root.ownsBrowseTarget = true;
        root.initialKind = ["mod", "shader", "resourcepack"].indexOf(kind) >= 0 ? kind : "mod";
        open();
    }
    function releaseTarget() {
        if (ownsBrowseTarget) { contentBridge.unpinBrowseTarget(); ownsBrowseTarget = false; }
    }
    Connections { target: root; function onAboutToHide() { root.releaseTarget(); } }
    Component.onDestruction: releaseTarget()
    background: PopupGlass {}
    Controls.Overlay.modal: Rectangle { color: "#aa080b12" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: GlassTheme.quick } }
    contentItem: Item {
        Button { id: back; objectName: "instanceLibraryBack"; width: parent.width; label: "‹  Quay lại quản lý · " + (root.instance.label || "Bản chơi"); quiet: true; clickable: !root.installing; onClicked: root.close() }
        Loader {
            anchors.top: back.bottom; anchors.topMargin: 12
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            active: root.opened
            sourceComponent: Component { Library { instanceScoped: true; instanceLabel: root.instance.label || root.instance.instanceId; kind: root.initialKind } }
        }
    }
}
