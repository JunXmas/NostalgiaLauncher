import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    objectName: "serverManagerDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(980 * GlassTheme.scale, parent ? parent.width - 40 : 980)
    height: Math.min(820 * GlassTheme.scale, parent ? parent.height - 40 : 820)
    x: parent ? (parent.width - width) / 2 : 0; y: parent ? (parent.height - height) / 2 : 0
    modal: true; dim: true; focus: true; padding: 24
    property int section: 0
    property string serverId: ""
    readonly property bool ready: serverBridge.selected.server_id === serverId
    readonly property bool running: serverBridge.runningId === serverId
    readonly property bool writable: ready && serverBridge.hasAccess && !serverBridge.busy && !serverBridge.runningId
    function openFor(serverId) { root.serverId = serverId; root.section = 0; serverBridge.select(serverId); root.open(); }
    background: Glass { padding: 0; backdrop: Legacy.Theme.modalBackdrop; blurOpacity: 0.9; color: GlassTheme.alpha(GlassTheme.surface, 0.89) }
    Controls.Overlay.modal: Rectangle { color: "#aa080b12" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    contentItem: Item {
        Column { id: header; width: parent.width - 46; spacing: 8
            PaymentText { width: parent.width; text: root.ready ? serverBridge.selected.display_name : "Đang đọc server…"; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont; elide: Text.ElideRight; maximumLineCount: 1 }
            PaymentText { width: parent.width; text: root.ready ? serverBridge.selected.engine_title + " · Minecraft " + serverBridge.selected.game_version + (root.running ? "  ·  ● Đang chạy" : "  ·  ○ Đã dừng") : ""; color: GlassTheme.muted }
        }
        Button { anchors.right: parent.right; width: 38; label: "×"; quiet: true; Accessible.name: "Đóng quản lý server"; onClicked: root.close() }
        Flow { id: tabs; anchors.top: header.bottom; anchors.topMargin: 18; width: parent.width; spacing: 6
            Repeater { model: ["Cấu hình", "Nội dung", "Console", "Nâng cao"]
                Button { objectName: "serverSection-" + index; label: modelData; selected: root.section === index; quiet: true; onClicked: root.section = index }
            }
        }
        Item {
            id: body
            anchors.top: tabs.bottom; anchors.topMargin: 18; anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: footer.top; anchors.bottomMargin: 14
            ServerSettings { id: settings; anchors.fill: parent; visible: root.section === 0; writable: root.writable }
            ServerContent { anchors.fill: parent; visible: root.section === 1; writable: root.writable }
            ServerConsole { anchors.fill: parent; visible: root.section === 2; running: root.running && root.ready }
            ServerAdvanced { anchors.fill: parent; visible: root.section === 3; writable: root.writable; serverId: root.serverId; onTrashRequested: root.close() }
        }
        Row { id: footer; anchors.right: parent.right; anchors.bottom: parent.bottom; spacing: 10
            Button { label: "Mở thư mục"; quiet: true; clickable: root.ready; onClicked: serverBridge.openFolder(root.serverId) }
            Button { objectName: "serverSettingsSave"; visible: root.section === 0; label: "Lưu cấu hình"; primary: true; clickable: root.writable; onClicked: settings.save() }
        }
    }
}
