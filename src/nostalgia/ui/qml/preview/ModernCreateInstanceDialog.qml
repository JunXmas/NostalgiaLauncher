import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Dialogs
import "../" as Legacy

Controls.Popup {
    id: dialog
    objectName: "modernCreateDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(1120 * GlassTheme.scale, parent ? parent.width - 48 : 1120)
    height: Math.min(body.implicitHeight + heading.implicitHeight + footer.height + 88 * GlassTheme.scale, parent ? parent.height - 48 : 760)
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
    readonly property bool wideLayout: body.width >= 900 * GlassTheme.scale
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
        Column {
            id: heading; width: parent.width - closeButton.width - 16; spacing: 6
            PaymentText { text: "Tạo bản chơi"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold }
            PaymentText { width: parent.width; text: "Chọn phiên bản và cách chơi cho thế giới của bạn."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        }
        Button { id: closeButton; anchors.right: parent.right; width: 36 * GlassTheme.scale; height: width; label: "×"; quiet: true; clickable: !bridge.busy; Accessible.name: "Đóng tạo bản chơi"; onClicked: dialog.close() }
        InertialScroll {
            objectName: "createFormScroll"
            anchors.top: heading.bottom; anchors.topMargin: 22 * GlassTheme.scale
            anchors.bottom: footer.top; anchors.bottomMargin: 18 * GlassTheme.scale; width: parent.width
            contentHeight: body.implicitHeight + 8
            Flow {
                id: body; width: parent.width - 8; spacing: 24 * GlassTheme.scale
                Column {
                    id: versionSection; objectName: "createVersionSection"
                    width: dialog.wideLayout ? (body.width - body.spacing) * 0.44 : body.width
                    spacing: 14 * GlassTheme.scale
                    PaymentText { text: "Phiên bản Minecraft"; font.weight: Font.DemiBold }
                    Item {
                        id: previewArea; width: parent.width
                        readonly property bool inlinePreview: !dialog.wideLayout && width > 560 * GlassTheme.scale
                        height: inlinePreview ? Math.max(artPanel.implicitHeight, versionControls.implicitHeight) : artPanel.implicitHeight + versionControls.implicitHeight + 18 * GlassTheme.scale
                        Column {
                            id: artPanel; width: previewArea.inlinePreview ? (previewArea.width - 18 * GlassTheme.scale) * 0.42 : previewArea.width
                            spacing: 10 * GlassTheme.scale
                            VersionArtwork { id: keyArt; objectName: "createVersionArtwork"; width: parent.width; gameVersion: dialog.gameVersion || (dialog.released.length ? dialog.released[0].versionId : "") }
                            PaymentText { width: parent.width; text: keyArt.title; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold }
                            PaymentText { width: parent.width; text: dialog.gameVersion ? "Minecraft " + dialog.gameVersion : "Ảnh xem trước · Chưa chọn phiên bản"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                        }
                        Column {
                            id: versionControls; objectName: "createVersionControls"
                            x: previewArea.inlinePreview ? artPanel.width + 18 * GlassTheme.scale : 0
                            y: previewArea.inlinePreview ? Math.max(0, (previewArea.height - implicitHeight) / 2) : artPanel.implicitHeight + 18 * GlassTheme.scale
                            width: previewArea.inlinePreview ? previewArea.width - x : previewArea.width; spacing: 10 * GlassTheme.scale
                            PaymentText { text: "Bản phát hành"; font.weight: Font.DemiBold }
                            Select { objectName: "createGameVersion"; width: parent.width; model: dialog.released.map(function(v) { return v.versionId; }); currentIndex: model.indexOf(dialog.gameVersion); displayText: dialog.gameVersion || (catalogBridge.busy ? "Đang tải phiên bản…" : "Chọn phiên bản…"); searchPlaceholder: "Tìm phiên bản Minecraft…"; enabled: !bridge.busy; onActivated: function(i) { if (i >= 0 && i < dialog.released.length) dialog.pickGameVersion(dialog.released[i].versionId); } }
                            PaymentText { width: parent.width; text: "Tìm nhanh hoặc chọn bản phát hành chính xác."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                        }
                    }
                }
                Column {
                    id: setupSection; objectName: "createSetupSection"
                    width: dialog.wideLayout ? body.width - versionSection.width - body.spacing : body.width
                    spacing: 16 * GlassTheme.scale
                    PaymentText { text: "Nền tảng & cấu hình"; font.weight: Font.DemiBold }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: dialog.loaderChoices
                            Button { objectName: "createLoader-" + modelData.key; width: Math.max(100 * GlassTheme.scale, (setupSection.width - 16) / 3); height: 44 * GlassTheme.scale; label: modelData.label; selected: dialog.loaderKind === modelData.key; onClicked: dialog.pickLoader(modelData.key) }
                        }
                    }
                    PaymentText { width: parent.width; text: dialog.isPreset ? "Fabric và các mod tối ưu được cài sẵn với Fabulously Optimized." : dialog.loaderKind === "vanilla" ? "Minecraft nguyên bản, không kèm mod loader." : "Cài mod dành cho " + dialog.loaderLabel + "."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                    Column { width: parent.width; spacing: 8; visible: dialog.needsLoaderStep
                        PaymentText { text: "Phiên bản " + dialog.loaderLabel; font.weight: Font.DemiBold }
                        Select { objectName: "createLoaderVersion"; width: parent.width; model: dialog.loaders.map(function(v) { return v.loaderVersion; }); currentIndex: model.indexOf(dialog.loaderVersion); displayText: dialog.loaderVersion || (catalogBridge.busy ? "Đang tải loader…" : "Chọn phiên bản loader…"); enabled: !!dialog.gameVersion && !bridge.busy && !catalogBridge.busy; onActivated: function(i) { if (i >= 0 && i < dialog.loaders.length) dialog.loaderVersion = dialog.loaders[i].loaderVersion; } }
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
        }
        Item {
            id: footer; objectName: "createDialogFooter"; anchors.bottom: parent.bottom; width: parent.width
            height: Math.max(footerActions.height, summary.implicitHeight)
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; y: -12 * GlassTheme.scale; height: 1; color: GlassTheme.stroke }
            Column { id: summary; width: Math.max(0, parent.width - footerActions.width - 20); visible: width > 180 * GlassTheme.scale; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                PaymentText { text: "Bản chơi của bạn"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                PaymentText { objectName: "createSelectionSummary"; width: parent.width; text: dialog.gameVersion ? dialog.loaderLabel + " · Minecraft " + dialog.gameVersion : "Chưa chọn phiên bản"; wrapMode: Text.NoWrap; elide: Text.ElideRight; font.weight: Font.DemiBold }
            }
            Row { id: footerActions; anchors.right: parent.right; spacing: 10
                Button { label: "Huỷ"; quiet: true; clickable: !bridge.busy; onClicked: dialog.close() }
                Button { objectName: "createInstanceConfirm"; label: bridge.busy ? "Đang cài…" : "Tạo bản chơi"; primary: true; clickable: dialog.canCreate; onClicked: catalogBridge.createInstance(nameField.text.trim() || dialog.defaultName, dialog.gameVersion, dialog.loaderKind, dialog.loaderVersion, parseInt(heapField.text) || 0, dialog.gameDirUrl) }
            }
        }
    }
    FolderDialog { id: folder; onAccepted: dialog.gameDirUrl = selectedFolder }
    Connections { target: catalogBridge; function onCreated(instanceId) { dialog.close(); } }
}
