import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    objectName: "serverCreateDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(790 * GlassTheme.scale, parent ? parent.width - 40 : 790)
    height: Math.min(820 * GlassTheme.scale, parent ? parent.height - 40 : 820)
    x: parent ? (parent.width - width) / 2 : 0; y: parent ? (parent.height - height) / 2 : 0
    modal: true; dim: true; focus: true; padding: 24
    property string engineId: "paper"
    property string gameVersion: ""
    property string buildId: ""
    property bool initialVersionsRequested: false
    readonly property var engine: serverBridge.engines.filter(function(e) { return e.engine_id === root.engineId; })[0] || ({})
    function chooseEngine(engineId) {
        root.initialVersionsRequested = true;
        root.engineId = engineId; root.gameVersion = ""; root.buildId = "";
        serverBridge.loadVersions(engineId);
    }
    closePolicy: serverBridge.busy ? Controls.Popup.NoAutoClose : Controls.Popup.CloseOnEscape
    function requestInitialVersions() { if (root.opened && !root.initialVersionsRequested && !serverBridge.busy) root.chooseEngine(root.engineId); }
    onOpened: { root.initialVersionsRequested = serverBridge.gameVersions.length > 0; root.requestInitialVersions(); }
    Connections { target: serverBridge; function onBusyChanged() { root.requestInitialVersions(); } }
    background: PopupGlass {}
    Controls.Overlay.modal: Rectangle { color: "#a8080b12" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal } }
    contentItem: Item {
        Column { id: title; width: parent.width - 46; spacing: 8
            PaymentText { width: parent.width; text: "Tạo server"; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
            PaymentText { width: parent.width; text: "Nền tảng của bạn. Thế giới của tất cả."; color: GlassTheme.muted }
        }
        Button { anchors.right: parent.right; width: 38; label: "×"; clickable: !serverBridge.busy; Accessible.name: "Đóng tạo server"; quiet: true; onClicked: root.close() }
        InertialScroll {
            objectName: "serverCreateScroll"
            anchors.top: title.bottom; anchors.topMargin: 20; anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: footer.top; anchors.bottomMargin: 16
            contentHeight: form.implicitHeight + 8
            Column { id: form; width: parent.width - 8; spacing: 16
                PaymentText { text: "NỀN TẢNG"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
                Grid {
                    id: engines
                    width: parent.width; columns: width > 620 ? 3 : 2; spacing: 10
                    Repeater {
                        model: serverBridge.engines
                        Button { objectName: "serverEngine-" + modelData.engine_id; width: (engines.width - (engines.columns - 1) * 10) / engines.columns; label: modelData.title; selected: root.engineId === modelData.engine_id; clickable: !serverBridge.busy; onClicked: root.chooseEngine(modelData.engine_id) }
                    }
                }
                PaymentText { width: parent.width; text: root.engine.description || ""; color: GlassTheme.muted }
                Glass { width: parent.width; padding: 14; height: hybridNote.implicitHeight + 28; visible: root.engineId.indexOf("arclight-") === 0 || root.engineId === "folia"
                    PaymentText { id: hybridNote; width: parent.width; text: root.engineId === "folia" ? "Folia phát hành bản Alpha và cần plugin hỗ trợ riêng. Nên thử với thế giới mới trước." : root.engineId === "arclight-forge" ? "Arclight Forge 1.21.1 hiện có bản lỗi từ nhà cung cấp và đã được loại khỏi danh mục. Chọn phiên bản khác hoặc dùng NeoForge/Fabric." : "Hybrid cần kiểm tra tương thích giữa mod và plugin. Thư viện chỉ gợi ý đúng phiên bản/loader; một số modpack vẫn cần tinh chỉnh riêng."; color: GlassTheme.muted }
                }
                PaymentText { text: "Phiên bản Minecraft"; font.weight: Font.DemiBold }
                Row { width: parent.width; spacing: 10
                    Select { objectName: "serverGameVersion"; width: Math.max(140, parent.width - loadVersions.width - 10); model: serverBridge.gameVersions; currentIndex: -1; displayText: root.gameVersion || "Chọn phiên bản…"; enabled: !serverBridge.busy; onActivated: function(i) { root.gameVersion = serverBridge.gameVersions[i]; root.buildId = ""; serverBridge.loadBuilds(root.engineId, root.gameVersion); } }
                    Button { id: loadVersions; label: "Tải danh mục"; clickable: !serverBridge.busy; onClicked: root.chooseEngine(root.engineId) }
                }
                PaymentText { text: "Bản server"; font.weight: Font.DemiBold }
                Select { objectName: "serverBuild"; width: parent.width; model: serverBridge.builds; currentIndex: -1; displayText: root.buildId || "Chọn bản phát hành…"; enabled: !serverBridge.busy && !!root.gameVersion; onActivated: function(i) { root.buildId = serverBridge.builds[i]; } }
                PaymentText { text: "Tên server"; font.weight: Font.DemiBold }
                Input { id: labelField; objectName: "serverLabel"; width: parent.width; text: "Thế giới cùng bạn"; placeholder: "Tên server của bạn" }
                PaymentText { width: parent.width; text: serverBridge.enabled ? serverBridge.note : "Host server trả phí đang tạm vô hiệu hoá. Bạn có thể xem nền tảng và danh mục; tạo server sẽ chờ tính năng được bật."; color: GlassTheme.muted }
                PaymentText { width: parent.width; visible: serverBridge.busy; text: serverBridge.activity; color: GlassTheme.accent }
            }
        }
        Row { id: footer; anchors.right: parent.right; anchors.bottom: parent.bottom; spacing: 10
            GuideButton { topicId: "server" }
            Button { visible: serverBridge.busy; label: "Huỷ tác vụ"; onClicked: serverBridge.cancel() }
            Button { objectName: "serverCreateSubmit"; label: "Tạo server"; primary: true; clickable: serverBridge.hasAccess && !serverBridge.busy && !!root.gameVersion && !!root.buildId && !!labelField.text.trim(); onClicked: serverBridge.create(labelField.text, root.engineId, root.gameVersion, root.buildId) }
        }
    }
}
