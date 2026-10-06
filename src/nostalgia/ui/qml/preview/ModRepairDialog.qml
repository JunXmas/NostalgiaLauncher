import QtQuick
import QtQuick.Controls as Controls

Controls.Popup {
    id: root
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
        }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
    objectName: "modRepairDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(800,parent ? parent.width - 48 : 800)
    height: Math.min(740,parent ? parent.height - 48 : 740)
    x: parent ? (parent.width-width)/2 : 0; y: parent ? (parent.height-height)/2 : 0
    padding: 24; modal: true; dim: true; focus: true
    property string instanceId: ""
    property string instanceLabel: ""
    property var details: modRepairBridge.details
    function openFor(instance) { instanceId=instance.instanceId;instanceLabel=instance.label;open();modRepairBridge.scan(instanceId); }
    background: Glass { padding: 0; radius: 24; color: GlassTheme.surface }
    Controls.Overlay.modal: Rectangle { color: "#aa080b12" }
    contentItem: Item {
        Column {
            id: header
            width: parent.width; spacing: 8
            PaymentText { width: parent.width-40; text: "Kiểm tra & sửa mod"; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
            PaymentText { width: parent.width; text: root.instanceLabel; color: GlassTheme.muted }
        }
        Button { anchors.right: parent.right; label: "×"; quiet: true; width: 40; Accessible.name: "Đóng kiểm tra mod"; onClicked: root.close() }
        InertialScroll {
            anchors.top: header.bottom; anchors.topMargin: 20; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: actions.top; anchors.bottomMargin: 18
            contentHeight: contents.implicitHeight+8
            Column {
                id: contents
                width: parent.width-8; spacing: 14
                PaymentText { objectName: "modRepairNote"; width: parent.width; text: modRepairBridge.busy ? "Đang kiểm tra…" : root.details.note; color: GlassTheme.accent }
                PaymentText { width: parent.width; text: "Free báo lỗi metadata. Plus lập phương án được hỗ trợ. Quét không chứng minh mọi mod chạy ổn trong game."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                Repeater { model: root.details.findings; Glass { width: contents.width; padding: 14; height: finding.implicitHeight+28; Column { id: finding; width: parent.width; spacing: 5; PaymentText { width: parent.width; text: modelData.file; font.weight: Font.DemiBold } PaymentText { width: parent.width; text: modelData.reason; color: modelData.code === "unknown" ? GlassTheme.muted : GlassTheme.danger } } } }
                PaymentText { width: parent.width; visible: root.details.changes.length>0; text: "PHƯƠNG ÁN PLUS"; font.weight: Font.DemiBold }
                Repeater { model: root.details.changes; PaymentText { width: contents.width; text: (modelData.operation === "add" ? "+ Thêm " : "− Tắt ") + modelData.file + "\n" + modelData.reason } }
                Repeater { model: root.details.unresolved; PaymentText { width: contents.width; text: "Chưa giải được: " + modelData; color: GlassTheme.danger } }
                PaymentText { width: parent.width; visible: root.details.canApply; text: "Sao lưu bộ mod, tải và kiểm hash, quét lại trước khi áp dụng. Thế giới chơi được giữ nguyên."; color: GlassTheme.muted }
            }
        }
        Flow {
            id: actions
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            spacing: 8
            Button { objectName: "modRescan"; label: "Quét lại"; clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: modRepairBridge.scan(root.instanceId) }
            Button { objectName: "modPlan"; label: "Lập phương án · Plus"; clickable: root.details.canPlan && !modRepairBridge.busy; onClicked: modRepairBridge.plan() }
            Button { objectName: "modApply"; label: "Áp dụng & sao lưu"; primary: true; visible: root.details.canApply; clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: confirmDialog.ask("Áp phương án sửa mod?","Các mod trong phương án sẽ được thêm/tắt. Giữ bản trước sửa để hoàn tác.",function(){modRepairBridge.apply();}) }
            Button { objectName: "modUndo"; label: "Hoàn tác"; visible: root.details.canUndo; clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: modRepairBridge.undo() }
        }
    }
}
