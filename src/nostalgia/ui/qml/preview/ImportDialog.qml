import QtQuick
import QtQuick.Dialogs

WorkspaceDialog {
    id: root
    objectName: "modernImportDialog"
    title: "Nhập bản chơi"
    guideTopic: "import"
    description: "Tiếp tục thế giới quen thuộc của bạn, từ modpack hoặc launcher khác."
    busy: importBridge.busy
    property int section: 0
    property string failure: ""
    function openDialog() { section = 0; failure = ""; open(); notifier.playUi("open"); importBridge.scanLaunchers(); }
    Connections {
        target: importBridge
        function onImportDone(instanceId) { root.close(); }
        function onImportError(message) { root.failure = message; }
        function onFailed(message) { root.failure = message; }
    }
    InertialScroll {
        objectName: "importBodyScroll"
        anchors.fill: parent
        contentHeight: importContent.implicitHeight + 8
        Column {
            id: importContent
            width: parent.width - 10; spacing: 18
            MotionTabs { width: parent.width; labels: ["File modpack", "Launcher khác"]; currentIndex: root.section; namePrefix: "importSection-"; onSelected: function(index) { if (!root.busy) root.section = index; } }
            Column {
                visible: root.section === 0
                width: parent.width; spacing: 14
                PaymentText { width: parent.width; text: "Mang modpack của bạn đến Nostalgia"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
                PaymentText { width: parent.width; text: "Chọn file .mrpack hoặc .zip. Launcher sẽ tạo bản chơi riêng cho modpack được nhập."; color: GlassTheme.muted }
                Button { objectName: "importChooseFile"; primary: true; label: "Chọn file modpack…"; clickable: !root.busy; onClicked: picker.open() }
                Glass { width: parent.width; height: warning.implicitHeight + 32; padding: 16; frosted: false
                    PaymentText { id: warning; width: parent.width; text: "Chỉ nhập modpack từ nguồn bạn tin tưởng. Mods có thể chạy mã trên máy tính của bạn."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                }
            }
            Column {
                visible: root.section === 1
                width: parent.width; spacing: 12
                Flow { width: parent.width; spacing: 12
                    Button { objectName: "importRescan"; label: "Quét lại"; quiet: true; clickable: !root.busy; onClicked: { root.failure = ""; importBridge.scanLaunchers(); } }
                    PaymentText { text: importBridge.scanResults.length + " bản chơi tìm thấy"; color: GlassTheme.muted }
                }
                PaymentText { visible: !root.busy && !importBridge.scanResults.length; width: parent.width; text: "Chưa tìm thấy bản chơi từ launcher khác trên máy này. Bạn vẫn có thể nhập bằng file modpack."; color: GlassTheme.muted }
                Repeater {
                    model: importBridge.scanResults
                    Glass {
                        width: importContent.width; height: details.implicitHeight + 32; padding: 16; frosted: false
                        Column {
                            id: details
                            width: parent.width; spacing: 10
                            PaymentText { width: parent.width; text: modelData.instanceName; font.weight: Font.DemiBold }
                            PaymentText { width: parent.width; text: modelData.launcher + " · " + (modelData.gameVersion || "Chưa rõ phiên bản") + " · " + modelData.loaderKind; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                            Button { objectName: "importExternal-" + index; label: "Nhập bản chơi"; clickable: !root.busy; onClicked: importBridge.importFromLauncher(index, "") }
                        }
                    }
                }
            }
        }
    }
    footer: Column {
        width: root.bodyWidth; spacing: 10
        PaymentText { objectName: "importStatus"; width: parent.width; text: root.failure || (root.busy ? importBridge.activity : ""); visible: !!text; color: root.failure ? GlassTheme.danger : GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
        Button { label: root.busy ? "Đang xử lý…" : "Đóng"; quiet: true; clickable: !root.busy; onClicked: root.close() }
    }
    FileDialog {
        id: picker; title: "Chọn modpack"; nameFilters: ["Modpack (*.mrpack *.zip)"]
        onAccepted: { root.failure = ""; importBridge.importMrpackFile(String(selectedFile), "", ""); }
    }
}
