import QtQuick
import "../" as Legacy

WorkspaceDialog {
    id: root
    objectName: "localModDialog"
    title: "Cài mod từ máy"
    description: "Chọn bản chơi sẽ nhận các file vừa kéo vào. File gốc trên máy bạn được giữ lại."
    guideTopic: "drop"
    preferredWidth: 720; preferredHeight: 620
    busy: localModBridge.busy
    z: 500
    property string instanceId: ""
    property bool replaceExisting: false
    readonly property var details: localModBridge.details
    readonly property bool writable: !busy && !bridge.busy && !bridge.storageBusy && !bridge.gameRunning && !contentBridge.busy
    Connections {
        target: localModBridge
        function onReviewRequested() { root.instanceId = ""; root.replaceExisting = false; root.open(); }
    }
    onClosed: localModBridge.clear()
    InertialScroll {
        objectName: "localModScroll"
        anchors.fill: parent; contentHeight: form.implicitHeight + 8
        Column {
            id: form; width: parent.width - 10; spacing: 16
            PaymentText { width: parent.width; text: "Cài vào bản chơi nào?"; font.weight: Font.DemiBold; font.pixelSize: GlassTheme.fontSubheading }
            Select {
                objectName: "localModInstance"
                width: parent.width
                model: bridge.instances.map(function(instance) { return instance.label + " · " + instance.versionId; })
                currentIndex: bridge.instances.findIndex(function(instance) { return instance.instanceId === root.instanceId; })
                displayText: currentIndex >= 0 ? textAt(currentIndex) : "Chọn bản chơi…"
                enabled: !root.busy
                onActivated: function(index) { root.instanceId = bridge.instances[index].instanceId; localModBridge.clearResult(); }
            }
            PaymentText { width: parent.width; visible: !bridge.instances.length; text: "Chưa có bản chơi. Đóng cửa sổ này, tạo bản chơi với loader phù hợp rồi kéo file vào lại."; color: GlassTheme.muted }
            PaymentText { width: parent.width; text: root.details.count + " file mod JAR" + (root.details.ignored ? " · bỏ qua " + root.details.ignored + " file không phải mod JAR" : ""); color: GlassTheme.muted }
            Repeater {
                model: root.details.files
                PaymentText { width: form.width; text: "• " + modelData; elide: Text.ElideMiddle; maximumLineCount: 1 }
            }
            Row {
                width: parent.width; spacing: 10
                Legacy.Toggle { checked: root.replaceExisting; enabled: !root.busy; accessibleLabel: "Thay file trùng tên và sao lưu bản cũ"; onToggled: function(value) { root.replaceExisting = value; localModBridge.clearResult(); } }
                PaymentText { width: parent.width - 58; text: "Thay file trùng tên · giữ bản cũ để khôi phục"; font.pixelSize: GlassTheme.fontNote }
            }
            Glass {
                width: parent.width; padding: 14; height: caution.implicitHeight + 28; frosted: false
                PaymentText { id: caution; width: parent.width; text: "Chỉ cài mod từ nguồn tin tưởng: JAR có thể chạy mã khi mở game. Bạn cần đúng phiên bản Minecraft và loader; việc chép file không tự cài phụ thuộc hay thêm loader cho Vanilla."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
            }
        }
    }
    footer: Column {
        width: root.bodyWidth; spacing: 10
        PaymentText { objectName: "localModStatus"; width: parent.width; text: root.busy ? "Đang cài mod…" : root.details.note || (bridge.gameRunning ? "Hãy đóng Minecraft trước khi cài mod." : bridge.storageBusy || bridge.busy || contentBridge.busy ? "Đợi thao tác hiện tại hoàn tất để cài mod." : ""); color: GlassTheme.muted; visible: !!text }
        Flow {
            width: parent.width; spacing: 10
            Button { objectName: "localModCancel"; label: root.details.done ? "Đóng" : "Hủy"; quiet: true; clickable: !root.busy; onClicked: root.close() }
            Button { objectName: "localModInstall"; label: "Cài vào bản chơi"; primary: true; clickable: root.writable && !!root.instanceId && root.details.count > 0; onClicked: localModBridge.install(root.instanceId, root.replaceExisting) }
        }
    }
}
