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
        InertialList {
            id: results
            objectName: "modRepairScroll"
            anchors.top: header.bottom; anchors.topMargin: 20; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: actions.top; anchors.bottomMargin: 18
            spacing: 14
            model: {
                var rows = (root.details.localFixes || []).map(function(f, i) { return {fix: f, position: i}; });
                (root.details.findings || []).forEach(function(f, i) { rows.push({finding: f, position: i}); });
                if ((root.details.changes || []).length) rows.push({heading: true});
                (root.details.recommendations || []).forEach(function(r) { rows.push({recommendation: r}); });
                (root.details.unresolved || []).forEach(function(u) { rows.push({unresolved: u}); });
                return rows;
            }
            header: Column {
                width: results.width - 8; spacing: 14; bottomPadding: 14
                PaymentText { objectName: "modRepairNote"; width: parent.width; text: modRepairBridge.busy ? Legacy.Tr.phrase("Đang xử lý…") : Legacy.Tr.message(root.details.note); color: GlassTheme.accent }
                PaymentText { width: parent.width; text: Legacy.Tr.phrase("Đọc lỗi crash và không tương thích từ log game. Chỉ đề xuất sửa khi xác định được yêu cầu phiên bản."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                PaymentText { width: parent.width; visible: root.details.scanned && root.details.logSources.length > 0; text: Legacy.Tr.phrase("Nguồn: ") + root.details.logSources.join(", ") + " · " + root.details.gameVersion + " / " + root.details.loader; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            }
            delegate: Loader {
                id: repairRow
                required property var modelData
                width: results.width - 8
                height: item ? item.height : 0
                sourceComponent: modelData.fix ? fixCard : modelData.finding ? findingCard : modelData.recommendation ? recommendationCard : modelData.heading ? sectionHeading : unresolvedText
                // Sửa tại chỗ, miễn phí: launcher tự làm được, không cần dịch vụ Plus.
                Component {
                    id: fixCard
                    Glass {
                        objectName: "modLocalFix-" + repairRow.modelData.position
                        width: repairRow.width; padding: 14; height: Math.max(fixTitle.implicitHeight + fixReason.implicitHeight + 5, 40) + 28
                        border.color: GlassTheme.accent
                        Column { id: fixText; width: parent.width - fixButton.width - 12; spacing: 5
                            PaymentText { id: fixTitle; width: parent.width; font.weight: Font.DemiBold
                                text: repairRow.modelData.fix.kind === "loader" ? Legacy.Tr.format("Nâng loader (%1)", [repairRow.modelData.fix.target])
                                    : repairRow.modelData.fix.kind === "disable" ? Legacy.Tr.format("Tắt %1", [repairRow.modelData.fix.target])
                                    : Legacy.Tr.format("Cài %1", [repairRow.modelData.fix.target]) }
                            PaymentText { id: fixReason; width: parent.width; text: Legacy.Tr.message(repairRow.modelData.fix.reason); color: GlassTheme.muted }
                        }
                        Button { id: fixButton; objectName: "modLocalFixApply-" + repairRow.modelData.position
                            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                            label: Legacy.Tr.phrase("Sửa ngay"); primary: true
                            disabledReason: bridge.gameRunning ? Legacy.Tr.phrase("Đóng Minecraft trước khi sửa bộ mod.") : ""
                            clickable: !modRepairBridge.busy && !disabledReason
                            onClicked: modRepairBridge.applyLocalFix(repairRow.modelData.position) }
                    }
                }
                Component {
                    id: findingCard
                    Glass {
                        objectName: "modLogFinding-" + repairRow.modelData.position
                        // Cộng thẳng hai dòng: chiều cao Column chưa cập nhật lúc ListView xếp hàng nên
                        // thẻ từng bị cắt nửa, dòng lý do tràn ra ngoài khung.
                        width: repairRow.width; padding: 14; height: findingFile.implicitHeight + findingReason.implicitHeight + 5 + 28
                        Column { id: finding; width: parent.width; spacing: 5
                            PaymentText { id: findingFile; width: parent.width; text: repairRow.modelData.finding.file; font.weight: Font.DemiBold }
                            PaymentText { id: findingReason; width: parent.width; text: Legacy.Tr.message(repairRow.modelData.finding.reason); color: repairRow.modelData.finding.severity === "error" ? GlassTheme.danger : GlassTheme.muted }
                        }
                    }
                }
                Component { id: recommendationCard; ModRepairCard { width: repairRow.width; modelData: repairRow.modelData.recommendation; onReplaceRequested: function(groupId) { modRepairBridge.replaceMod(groupId); } } }
                Component { id: sectionHeading; PaymentText { width: repairRow.width; text: Legacy.Tr.phrase("PHƯƠNG ÁN PLUS"); font.weight: Font.DemiBold } }
                Component { id: unresolvedText; PaymentText { width: repairRow.width; text: Legacy.Tr.phrase("Chưa giải được: ") + Legacy.Tr.message(repairRow.modelData.unresolved); color: GlassTheme.danger } }
            }
            footer: PaymentText { width: results.width - 8; visible: root.details.canApply; text: Legacy.Tr.phrase("Sao lưu bộ mod, tải và kiểm hash, quét lại trước khi áp dụng. Thế giới chơi được giữ nguyên."); color: GlassTheme.muted }
        }
        Flow {
            id: actions
            GuideButton { topicId: "repair" }
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            spacing: 8
            Button { objectName: "modRescan"; label: Legacy.Tr.phrase("Đọc lại log"); clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: modRepairBridge.scan(root.instanceId) }
            Button { objectName: "modPlan"; label: Legacy.Tr.phrase("Tìm bản phù hợp · Plus"); visible: plusFeaturesEnabled && root.details.canPlan; clickable: !modRepairBridge.busy; onClicked: modRepairBridge.plan() }
            // Bản cũ ẩn nút im lặng khi không có Plus: người dùng tưởng tính năng hỏng. Nói rõ.
            PaymentText { objectName: "modPlanUnavailable"; visible: !root.details.canPlan && root.details.scanned && !(root.details.localFixes || []).length && (root.details.findings || []).length > 0
                width: parent.width; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote
                text: Legacy.Tr.phrase("Chưa có cách sửa tự động cho lỗi này. Tìm bản thay thế cần đăng nhập Nostalgia+.") }
            Button { objectName: "modApply"; label: Legacy.Tr.phrase("Áp dụng tất cả & sao lưu"); primary: true; visible: root.details.canApply; clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: confirmDialog.ask(Legacy.Tr.phrase("Áp phương án sửa mod?"),Legacy.Tr.phrase("Các mod trong phương án sẽ được thêm/tắt. Giữ bản trước sửa để hoàn tác."),function(){modRepairBridge.apply();}) }
            Button { objectName: "modUndo"; label: Legacy.Tr.phrase("Hoàn tác"); visible: root.details.canUndo; clickable: !modRepairBridge.busy && !bridge.gameRunning; onClicked: modRepairBridge.undo() }
        }
    }
}
