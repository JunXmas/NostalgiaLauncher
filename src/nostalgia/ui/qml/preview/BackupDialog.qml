import QtQuick
import QtQuick.Dialogs
import "../" as Legacy

WorkspaceDialog {
    id: root
    objectName: "modernBackupDialog"
    title: "Xuất modpack"
    guideTopic: "backup"
    description: "Đóng gói bản chơi để chia sẻ hoặc nhập lại trên máy khác."
    busy: storageBridge.busy
    preferredWidth: 800
    property string instanceId: ""
    property string archiveFormat: "mrpack"
    property string statusMessage: ""
    property string exportedPath: ""
    property bool failed: false
    property bool legacyRequested: false
    readonly property bool canExport: !!instanceId && !root.busy && !bridge.gameRunning && !bridge.busy
    function openDialog(selectedId) {
        instanceId = selectedId || (bridge.instances.length ? bridge.instances[0].instanceId : "");
        statusMessage = ""; exportedPath = ""; failed = false; worlds.checked = false;
        storageBridge.refresh(); open(); notifier.playUi("open");
    }
    function saveTo(fileUrl) {
        if (canExport) { statusMessage = ""; failed = false; storageBridge.exportModpack(instanceId, String(fileUrl), archiveFormat, worlds.checked); }
    }
    onClosed: { if (legacyRequested) { legacyRequested = false; legacy.openDialog(); } }
    Connections {
        target: storageBridge
        function onCompleted(message) { root.statusMessage = message; root.failed = false; }
        function onFailed(message) { root.statusMessage = message; root.failed = true; }
        function onModpackExported(path) { root.exportedPath = path; }
    }
    InertialScroll {
        objectName: "exportBodyScroll"
        anchors.fill: parent
        contentHeight: form.implicitHeight + 8
        Column {
            id: form
            width: parent.width - 10; spacing: 18
            PaymentText { text: "Bản chơi cần đóng gói"; font.weight: Font.DemiBold }
            Select {
                objectName: "exportInstancePicker"
                width: parent.width
                model: bridge.instances.map(function(instance) { return instance.label + " · " + instance.versionId; })
                currentIndex: Math.max(0, bridge.instances.findIndex(function(instance) { return instance.instanceId === root.instanceId; }))
                enabled: !root.busy
                onActivated: function(index) { root.instanceId = bridge.instances[index].instanceId; }
            }
            PaymentText { visible: !bridge.instances.length; width: parent.width; text: "Chưa có bản chơi để xuất. Hãy tạo hoặc nhập một bản chơi trước."; color: GlassTheme.muted }
            MotionTabs { objectName: "exportFormats"; width: parent.width; labels: ["MRPACK", "ZIP"]; namePrefix: "exportFormat-"; currentIndex: root.archiveFormat === "mrpack" ? 0 : 1; onSelected: function(index) { if (!root.busy) root.archiveFormat = index ? "zip" : "mrpack"; } }
            Glass {
                width: parent.width; height: formatText.implicitHeight + 36; padding: 18
                Column { id: formatText; width: parent.width; spacing: 10
                    PaymentText { width: parent.width; text: root.archiveFormat === "mrpack" ? "Modrinth · MRPACK" : "Modpack · ZIP"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: root.archiveFormat === "mrpack" ? "Định dạng Modrinth, có thể nhập bằng Nostalgia hoặc launcher hỗ trợ MRPACK." : "File ZIP theo định dạng modpack CurseForge, có thể nhập lại trong Nostalgia."; color: GlassTheme.muted }
                    PaymentText { width: parent.width; text: "Gồm mods đang bật/tắt, resourcepack, shader và cấu hình. Giữ đúng phiên bản Minecraft và loader; đóng gói trực tiếp các file đang có trên máy."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                }
            }
            Glass {
                width: parent.width; height: worldNote.implicitHeight + 40; padding: 18
                Row { width: parent.width; spacing: 14
                    Legacy.Toggle { id: worlds; objectName: "exportIncludeWorlds"; anchors.verticalCenter: parent.verticalCenter; enabled: !root.busy; accessibleLabel: "Đóng gói cả thế giới"; onToggled: function(value) { checked = value; } }
                    Column { id: worldNote; width: parent.width - worlds.width - 14; spacing: 8
                        PaymentText { width: parent.width; text: "Đóng gói cả thế giới"; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: worlds.checked ? "Thư mục saves sẽ đi cùng modpack. File có thể lớn hơn và chứa thế giới cá nhân của bạn." : "Chỉ chia sẻ modpack. Thế giới đã chơi được giữ riêng trên máy bạn."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                    }
                }
            }
            PaymentText { visible: !!root.exportedPath; width: parent.width; text: root.exportedPath; color: GlassTheme.muted; wrapMode: Text.WrapAnywhere; font.pixelSize: GlassTheme.fontNote }
            Flow { width: parent.width; spacing: 10
                Button { objectName: "exportOpenFolder"; label: "Mở thư mục xuất"; quiet: true; onClicked: storageBridge.openExportsFolder(root.exportedPath) }
                Button { objectName: "openLegacyBackups"; visible: storageBridge.backups.length > 0 || storageBridge.trash.length > 0; label: "Khôi phục dữ liệu cũ"; quiet: true; clickable: !root.busy; onClicked: { root.legacyRequested = true; root.close(); } }
            }
        }
    }
    footer: Column {
        width: root.bodyWidth; spacing: 10
        PaymentText { objectName: "exportStatus"; width: parent.width; text: root.statusMessage || (root.busy ? storageBridge.activity : "Chọn nơi lưu file. Bản chơi gốc được giữ nguyên."); color: root.failed ? GlassTheme.danger : GlassTheme.muted; maximumLineCount: 3; elide: Text.ElideRight; font.pixelSize: GlassTheme.fontNote }
        Button { objectName: "exportSaveButton"; label: root.busy ? "Đang đóng gói…" : "Xuất " + root.archiveFormat.toUpperCase() + "…"; primary: true; clickable: root.canExport; onClicked: { picker.selectedFile = storageBridge.suggestedExportFile(root.instanceId, root.archiveFormat); picker.open(); } }
    }
    FileDialog {
        id: picker; objectName: "exportSavePicker"; title: "Lưu modpack"
        fileMode: FileDialog.SaveFile; defaultSuffix: root.archiveFormat
        nameFilters: root.archiveFormat === "mrpack" ? ["Modrinth modpack (*.mrpack)"] : ["Modpack ZIP (*.zip)"]
        onAccepted: root.saveTo(selectedFile)
    }
    LegacyBackupDialog { id: legacy }
}
