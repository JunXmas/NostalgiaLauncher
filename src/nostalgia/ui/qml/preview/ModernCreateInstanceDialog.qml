import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Dialogs
import "../" as Legacy

Controls.Popup {
    id: dialog
    objectName: "modernCreateDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(880 * GlassTheme.scale, parent ? parent.width - 32 : 880)
    height: Math.min(body.implicitHeight + 150 * GlassTheme.scale, parent ? parent.height - 32 : 720)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    modal: true; dim: true; focus: true; padding: 24 * GlassTheme.scale
    closePolicy: bridge.busy ? Controls.Popup.NoAutoClose : Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutside
    property string loaderKind: "optimized"
    property string gameVersion: ""
    property string loaderVersion: ""
    property string expandedMajor: ""
    property string gameDirUrl: ""
    property bool advancedOpen: false
    readonly property var released: catalogBridge.releasedVersions
    readonly property var presetVersions: catalogBridge.presetGameVersions
    readonly property var loaders: catalogBridge.loaderVersions
    readonly property var loaderChoices: [
        {key: "optimized", label: "Optimized"}, {key: "vanilla", label: "Vanilla"},
        {key: "fabric", label: "Fabric"}, {key: "quilt", label: "Quilt"},
        {key: "forge", label: "Forge"}, {key: "neoforge", label: "NeoForge"}]
    readonly property string loaderLabel: (loaderChoices.find(function(c) { return c.key === dialog.loaderKind; }) || {}).label || loaderKind
    readonly property bool isPreset: loaderKind === "optimized"
    readonly property bool needsLoaderStep: !isPreset && loaderKind !== "vanilla"
    readonly property string defaultName: loaderLabel + " " + gameVersion
    readonly property bool versionUnsupported: isPreset && !!gameVersion && presetVersions.length > 0 && presetVersions.indexOf(gameVersion) < 0
    readonly property string missingStep: !gameVersion ? "Chọn phiên bản Minecraft để tiếp tục." : versionUnsupported ? "Bản tối ưu chưa hỗ trợ " + gameVersion + ". Bạn có thể chọn Fabric hoặc phiên bản khác." : needsLoaderStep && !loaderVersion ? "Chọn phiên bản " + loaderLabel + "." : ""
    readonly property bool canCreate: !missingStep && !bridge.busy && !catalogBridge.busy
    function openDialog() {
        loaderKind = "optimized"; gameVersion = ""; loaderVersion = ""; gameDirUrl = "";
        advancedOpen = false; nameField.text = ""; heapField.text = "";
        open(); notifier.playUi("open");
        if (!released.length) catalogBridge.loadReleasedVersions();
        catalogBridge.loadPresetVersions();
    }
    function pickGameVersion(versionId) {
        gameVersion = versionId; loaderVersion = "";
        if (needsLoaderStep) catalogBridge.loadLoaderVersions(loaderKind, versionId);
    }
    function pickLoader(kind) {
        loaderKind = kind; loaderVersion = "";
        if (needsLoaderStep && gameVersion) catalogBridge.loadLoaderVersions(kind, gameVersion);
    }
    background: Glass { padding: 0; backdrop: Legacy.Theme.modalBackdrop; color: GlassTheme.alpha(GlassTheme.surface, 0.88); blurOpacity: 0.95 }
    Controls.Overlay.modal: Rectangle { color: "#99080b12" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: GlassTheme.quick } }
    contentItem: Item {
        PaymentText { id: heading; width: parent.width - closeButton.width - 12; text: "Tạo bản chơi"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold }
        Button { id: closeButton; anchors.right: parent.right; width: 36; label: "×"; quiet: true; clickable: !bridge.busy; Accessible.name: "Đóng tạo bản chơi"; onClicked: dialog.close() }
        InertialScroll {
            objectName: "createFormScroll"
            anchors.top: heading.bottom; anchors.topMargin: 22 * GlassTheme.scale
            anchors.bottom: footer.top; anchors.bottomMargin: 16; width: parent.width
            contentHeight: body.implicitHeight + 8
            Column {
                id: body; width: parent.width - 8; spacing: 18 * GlassTheme.scale
                PaymentText { width: parent.width; text: "Một thế giới mới, theo cách của bạn."; color: GlassTheme.muted }
                PaymentText { text: "Nền tảng"; font.weight: Font.DemiBold }
                Flow {
                    width: parent.width; spacing: 8
                    Repeater {
                        model: dialog.loaderChoices
                        Button {
                            objectName: "createLoader-" + modelData.key
                            width: Math.max(110 * GlassTheme.scale, (body.width - 16) / 3)
                            height: 52 * GlassTheme.scale; label: modelData.label
                            selected: dialog.loaderKind === modelData.key
                            onClicked: dialog.pickLoader(modelData.key)
                        }
                    }
                }
                PaymentText { width: parent.width; text: dialog.isPreset ? "Fabric và các mod tối ưu được cài sẵn với Fabulously Optimized." : dialog.loaderKind === "vanilla" ? "Minecraft nguyên bản, không kèm mod loader." : "Cài mod dành cho " + dialog.loaderLabel + "."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                Grid {
                    width: parent.width; columns: width > 600 * GlassTheme.scale ? 2 : 1; spacing: 14
                    Column { width: parent.columns === 2 ? (parent.width - 14) / 2 : parent.width; spacing: 8
                        PaymentText { text: "Minecraft"; font.weight: Font.DemiBold }
                        Select { objectName: "createGameVersion"; width: parent.width; model: dialog.released.map(function(v) { return v.versionId; }); currentIndex: model.indexOf(dialog.gameVersion); displayText: dialog.gameVersion || (catalogBridge.busy ? "Đang tải phiên bản…" : "Chọn phiên bản…"); searchPlaceholder: "Tìm phiên bản Minecraft…"; enabled: !bridge.busy; onActivated: function(i) { if (i >= 0 && i < dialog.released.length) dialog.pickGameVersion(dialog.released[i].versionId); } }
                    }
                    Column { width: parent.columns === 2 ? (parent.width - 14) / 2 : parent.width; spacing: 8; visible: dialog.needsLoaderStep
                        PaymentText { text: dialog.loaderLabel; font.weight: Font.DemiBold }
                        Select { objectName: "createLoaderVersion"; width: parent.width; model: dialog.loaders.map(function(v) { return v.loaderVersion; }); currentIndex: model.indexOf(dialog.loaderVersion); displayText: dialog.loaderVersion || (catalogBridge.busy ? "Đang tải loader…" : "Chọn phiên bản loader…"); enabled: !!dialog.gameVersion && !bridge.busy && !catalogBridge.busy; onActivated: function(i) { if (i >= 0 && i < dialog.loaders.length) dialog.loaderVersion = dialog.loaders[i].loaderVersion; } }
                    }
                }
                Column { width: parent.width; spacing: 8
                    PaymentText { text: "Tên bản chơi"; font.weight: Font.DemiBold }
                    Input { id: nameField; objectName: "createInstanceName"; width: parent.width; placeholder: dialog.gameVersion ? dialog.defaultName : "Đặt tên, hoặc dùng tên tự động" }
                }
                Button { label: dialog.advancedOpen ? "Thiết lập nâng cao  ⌃" : "Thiết lập nâng cao  ⌄"; quiet: true; onClicked: dialog.advancedOpen = !dialog.advancedOpen }
                Column { visible: dialog.advancedOpen; width: parent.width; spacing: 10
                    Input { id: heapField; width: parent.width; placeholder: "RAM (MB) · để trống dùng cài đặt mặc định" }
                    Flow { width: parent.width; spacing: 8
                        Button { label: "Chọn thư mục chơi"; onClicked: folder.open() }
                        PaymentText { width: Math.max(160, parent.width - 220 * GlassTheme.scale); text: dialog.gameDirUrl || "Thư mục mặc định của launcher"; color: GlassTheme.muted; wrapMode: Text.WrapAnywhere }
                    }
                }
                PaymentText { width: parent.width; text: dialog.missingStep || (catalogBridge.busy ? catalogBridge.activity : ""); color: dialog.versionUnsupported ? GlassTheme.danger : GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
        }
        Row { id: footer; anchors.right: parent.right; anchors.bottom: parent.bottom; spacing: 10
            Button { label: "Huỷ"; quiet: true; clickable: !bridge.busy; onClicked: dialog.close() }
            Button { objectName: "createInstanceConfirm"; label: bridge.busy ? "Đang cài…" : "Tạo bản chơi"; primary: true; clickable: dialog.canCreate; onClicked: catalogBridge.createInstance(nameField.text.trim() || dialog.defaultName, dialog.gameVersion, dialog.loaderKind, dialog.loaderVersion, parseInt(heapField.text) || 0, dialog.gameDirUrl) }
        }
    }
    FolderDialog { id: folder; onAccepted: dialog.gameDirUrl = selectedFolder }
    Connections { target: catalogBridge; function onCreated(instanceId) { dialog.close(); } }
}
