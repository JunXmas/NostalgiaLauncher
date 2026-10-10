import QtQuick
import "../" as Legacy
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
    background: PopupGlass {}
    Controls.Overlay.modal: Rectangle { color: "#aa080b12" }
    contentItem: Item {
        Column {
            id: header
            width: parent.width; spacing: 8
            PaymentText { width: parent.width-40; text: Legacy.Tr.phrase("Sửa lỗi mod từ log"); font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
            PaymentText { width: parent.width; text: root.instanceLabel; color: GlassTheme.muted }
        }
        Button { anchors.right: parent.right; label: "×"; quiet: true; width: 40; Accessible.name: Legacy.Tr.phrase("Đóng kiểm tra mod"); onClicked: root.close() }
        InertialScroll {
            objectName: "modRepairScroll"
            anchors.top: header.bottom; anchors.topMargin: 20; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: actions.top; anchors.bottomMargin: 18
            contentHeight: contents.implicitHeight+8
            Column {
                id: contents
                width: parent.width-8; spacing: 14
                PaymentText { objectName: "modRepairNote"; width: parent.width; text: modRepairBridge.busy ? Legacy.Tr.phrase("Đang xử lý…") : Legacy.Tr.message(root.details.note); color: GlassTheme.accent }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Đọc lỗi crash và không tương thích từ log game. Chỉ đề xuất sửa khi xác định được yêu cầu phiên bản."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                PaymentText { width: parent.width; visible: root.details.scanned && root.details.logSources.length > 0; text: Legacy.Tr.phrase("Nguồn: ") + root.details.logSources.join(", ") + " · " + root.details.gameVersion + " / " + root.details.loader; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                Repeater { model: root.details.findings; Glass { objectName: "modLogFinding-" + index; width: contents.width; padding: 14; height: finding.implicitHeight+28; Column { id: finding; width: parent.width; spacing: 5; PaymentText { width: parent.width; text: modelData.file; font.weight: Font.DemiBold } PaymentText { width: parent.width; text: Legacy.Tr.message(modelData.reason); color: modelData.severity === "error" ? GlassTheme.danger : GlassTheme.muted } } } }
                PaymentText { width: parent.width; visible: root.details.changes.length>0; text: Legacy.Tr.phrase("PHƯƠNG ÁN PLUS"); font.weight: Font.DemiBold }
                Repeater { model: root.details.recommendations; ModRepairCard { width: contents.width; onReplaceRequested: function(groupId) { modRepairBridge.replaceMod(groupId); } } }
                Repeater { model: root.details.unresolved; PaymentText { width: contents.width; text: Legacy.Tr.phrase("Chưa giải được: ") + Legacy.Tr.message(modelData); color: GlassTheme.danger } }
                PaymentText { width: parent.width; visible: root.details.canApply; text: Legacy.Tr.phrase("Sao lưu bộ mod, tải và kiểm hash, quét lại trước khi áp dụng. Thế giới chơi được giữ nguyên."); color: GlassTheme.muted }
            }
        }
        Flow {
            id: actions
            GuideButton { topicId: "repair" }
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            spacing: 8
            Button { objectName: "modRescan"; label: Legacy.Tr.phrase("Đọc lại log"); clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: modRepairBridge.scan(root.instanceId) }
            Button { objectName: "modPlan"; label: Legacy.Tr.phrase("Tìm bản phù hợp · Plus"); visible: plusFeaturesEnabled && root.details.canPlan; clickable: !modRepairBridge.busy; onClicked: modRepairBridge.plan() }
            Button { objectName: "modApply"; label: Legacy.Tr.phrase("Áp dụng tất cả & sao lưu"); primary: true; visible: root.details.canApply; clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: confirmDialog.ask(Legacy.Tr.phrase("Áp phương án sửa mod?"),Legacy.Tr.phrase("Các mod trong phương án sẽ được thêm/tắt. Giữ bản trước sửa để hoàn tác."),function(){modRepairBridge.apply();}) }
            Button { objectName: "modUndo"; label: Legacy.Tr.phrase("Hoàn tác"); visible: root.details.canUndo; clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: modRepairBridge.undo() }
        }
    }
}
