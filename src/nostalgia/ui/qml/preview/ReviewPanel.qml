import QtQuick
import QtQuick.Controls as Controls

Item {
    id: panel
    Button {
        objectName: "draftToolsOpen"
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 4
        height: 26; label: "Ultimate TEST · Công cụ Draft"
        onClicked: tools.open()
    }
    Controls.Popup {
        id: tools; objectName: "draftToolsDialog"
        parent: Controls.Overlay.overlay
        width: Math.min(650, parent.width - 40)
        height: Math.min(520, parent.height - 40)
        x: (parent.width - width) / 2; y: (parent.height - height) / 2
        modal: true; dim: true; focus: true; padding: 24
        background: Glass { padding: 0; color: GlassTheme.alpha(GlassTheme.surface, 0.90) }
        Controls.Overlay.modal: Rectangle { color: "#a8080b12" }
        contentItem: Item {
            Button { anchors.top: parent.top; anchors.right: parent.right; width: 36; label: "×"; quiet: true; onClicked: tools.close() }
            InertialScroll {
                objectName: "draftToolsScroll"
                anchors.fill: parent; anchors.topMargin: 42
                contentHeight: form.implicitHeight + 8
                Column {
                    id: form; width: parent.width - 8; spacing: 16
                    PaymentText { width: parent.width; text: "Bản thử nội bộ"; font.pixelSize: GlassTheme.fontDialog }
                    PaymentText { width: parent.width; text: "Mặc định mở Ultimate. Server, cosmetic và sửa mod chạy trên dữ liệu local. Bạn bè/chat và thanh toán là mô phỏng. Google và đồng bộ giữa hai máy cần backend thật."; color: GlassTheme.muted }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: [{name: "Plus", id: "plus-month-v1"}, {name: "Pro", id: "plus-half-year-v1"}, {name: "Max", id: "plus-year-v2"}, {name: "Ultimate", id: "plus-lifetime-v1"}]
                            Button { objectName: "draftPlan-" + modelData.id; label: modelData.name; clickable: !draftReviewController.busy; onClicked: draftReviewController.selectPlan(modelData.id) }
                        }
                    }
                    PaymentText { width: parent.width; text: "Đồng bộ local sẽ tạo một bản chơi mới từ modpack bạn chọn; không gửi file cho người khác."; color: GlassTheme.muted }
                    Select { id: source; objectName: "draftSyncSource"; width: parent.width; model: bridge.instances; textRole: "label"; currentIndex: model.length ? 0 : -1 }
                    Button { objectName: "draftSyncLocal"; label: "Đồng bộ local · Tạo bản chơi mới"; clickable: source.currentIndex >= 0 && !draftReviewController.busy; onClicked: draftReviewController.syncLocal(bridge.instances[source.currentIndex].instanceId) }
                    Button { objectName: "draftSimulatePaid"; label: "Mô phỏng thanh toán thành công"; clickable: !draftReviewController.busy && paymentBridge.details.stage === "pending"; onClicked: draftReviewController.simulatePaid() }
                    PaymentText { width: parent.width; text: draftReviewController.busy ? draftReviewController.activity : draftReviewController.note; color: GlassTheme.accent }
                }
            }
        }
    }
}
