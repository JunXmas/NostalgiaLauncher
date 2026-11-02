import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Item {
    id: root
    objectName: "serverContentPanel"
    property bool writable: false
    property string kind: "plugin"
    property string source: "modrinth"
    property string projectId: ""
    property string versionId: ""
    property string loadedKey: ""
    property bool autoPending: false
    readonly property string selectionKey: (serverBridge.selected.server_id || "") + ":" + source + ":" + kind
    function scheduleLibrary() {
        if (!visible || !serverBridge.selected.server_id || !(supportsPlugins || supportsMods)) {
            autoPending = false; autoSearch.stop(); return;
        }
        if (loadedKey !== selectionKey) {
            autoPending = true; autoSearch.restart();
        }
    }
    function searchLibrary() {
        root.autoPending = false; root.loadedKey = root.selectionKey;
        root.projectId = ""; root.versionId = "";
        serverBridge.search(root.source, root.kind, query.text);
    }
    function resetLibrary() { root.projectId = ""; root.versionId = ""; serverBridge.clearContent(); root.loadedKey = ""; root.scheduleLibrary(); }
    onVisibleChanged: { if (visible) scheduleLibrary(); else { autoPending = false; autoSearch.stop(); } }
    onSelectionKeyChanged: scheduleLibrary()
    Timer { id: autoSearch; interval: 80; onTriggered: { if (!root.visible || !root.autoPending) return; if (serverBridge.busy) restart(); else root.searchLibrary(); } }
    Connections { target: serverBridge; function onSelectionLoaded() { root.loadedKey = ""; root.scheduleLibrary(); } }
    readonly property var engine: serverBridge.engines.filter(function(e) { return e.engine_id === serverBridge.selected.engine_id; })[0] || ({})
    readonly property bool supportsPlugins: engine.supports_plugins === true
    readonly property bool supportsMods: !!engine.mod_loader
    onSupportsPluginsChanged: { root.kind = supportsPlugins ? "plugin" : "mod"; root.source = "modrinth"; }
    Column { id: header; width: parent.width; spacing: 12
        Flow { width: parent.width; spacing: 8
            GuideButton { topicId: "plugin" }
            Button { label: "Plugin"; visible: root.supportsPlugins; selected: root.kind === "plugin"; clickable: !serverBridge.busy; onClicked: { root.kind = "plugin"; root.resetLibrary(); } }
            Button { label: "Mod"; visible: root.supportsMods; selected: root.kind === "mod"; clickable: !serverBridge.busy; onClicked: { root.kind = "mod"; root.source = "modrinth"; root.resetLibrary(); } }
            Select { objectName: "serverContentSource"; currentIndex: root.source === "hangar" ? 1 : 0; width: 180 * GlassTheme.scale; model: root.kind === "plugin" && ["paper", "purpur", "folia"].indexOf(serverBridge.selected.engine_id) >= 0 ? ["Modrinth", "Hangar"] : ["Modrinth"]; enabled: !serverBridge.busy; onActivated: function(i) { root.source = i === 1 ? "hangar" : "modrinth"; root.resetLibrary(); } }
        }
        Row { width: parent.width; spacing: 10
            Input { id: query; objectName: "serverContentQuery"; width: Math.max(140, parent.width - search.width - 10); placeholder: root.kind === "plugin" ? Legacy.Tr.phrase("Tìm plugin tương thích…") : Legacy.Tr.phrase("Tìm mod dành cho server…"); onAccepted: search.trigger() }
            Button { id: search; objectName: "serverContentSearch"; label: Legacy.Tr.phrase("Tìm kiếm"); primary: true; clickable: !serverBridge.busy && (root.supportsPlugins || root.supportsMods); onClicked: root.searchLibrary() }
        }
        PaymentText { width: parent.width; text: serverBridge.busy ? Legacy.Tr.message(serverBridge.activity) : root.supportsPlugins || root.supportsMods ? Legacy.Tr.phrase("Lọc theo Minecraft ") + (serverBridge.selected.game_version || "") + Legacy.Tr.phrase(" và ") + (serverBridge.selected.engine_title || "") + Legacy.Tr.phrase(". Hangar chỉ hiển thị bản Release tải trực tiếp, không cần dependency ngoài.") : Legacy.Tr.phrase("Vanilla không hỗ trợ plugin hoặc mod."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
    }
    readonly property int resultColumns: width - 8 > 640 * GlassTheme.scale ? 2 : 1
    readonly property var resultRows: {
        var rows = [];
        for (var i = 0; i < serverBridge.projects.length; i += resultColumns)
            rows.push({projects: serverBridge.projects.slice(i, i + resultColumns)});
        rows.push({summary: true});
        serverBridge.installed.forEach(function(content) { rows.push({installed: content}); });
        return rows;
    }
    InertialList {
        id: libraryViewport
        objectName: "serverContentScroll"
        anchors.top: header.bottom; anchors.topMargin: 14
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        spacing: 12
        model: root.resultRows
        header: Item {
            width: libraryViewport.width - 8; height: explore.implicitHeight + 14
            PaymentText { id: explore; text: query.text ? Legacy.Tr.phrase("Kết quả tìm kiếm") : Legacy.Tr.phrase("Khám phá ") + (root.kind === "plugin" ? "plugin" : "mod"); font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold }
        }
        delegate: Loader {
            id: resultRow
            required property var modelData
            width: libraryViewport.width - 8
            height: item ? item.implicitHeight : 0
            sourceComponent: modelData.projects ? projectGroup : modelData.installed ? installedRow : summaryRow
            Component {
                id: projectGroup
                Row {
                    width: resultRow.width; spacing: 12
                    Repeater {
                        model: resultRow.modelData.projects
                        ServerProjectTile {
                            required property var modelData
                            width: (resultRow.width - (root.resultColumns - 1) * 12) / root.resultColumns
                            project: modelData; clickable: !serverBridge.busy
                            renderEnabled: libraryViewport.visible && resultRow.y + resultRow.height >= libraryViewport.contentY && resultRow.y <= libraryViewport.contentY + libraryViewport.height
                            onChosen: { root.projectId = modelData.project_id; root.source = modelData.source; root.versionId = ""; serverBridge.loadContentVersions(root.source, root.kind, root.projectId); versionPopup.open(); }
                        }
                    }
                }
            }
            Component {
                id: summaryRow
                Column {
                    width: resultRow.width; spacing: 12
                    PaymentText { width: parent.width; visible: !serverBridge.projects.length; text: serverBridge.busy || root.autoPending ? Legacy.Tr.phrase("Đang tìm nội dung tương thích…") : Legacy.Tr.phrase("Không tìm thấy nội dung tương thích. Thử từ khoá khác hoặc đổi nguồn."); color: GlassTheme.muted }
                    PaymentText { width: parent.width; visible: !!serverBridge.note; text: Legacy.Tr.message(serverBridge.note); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                    PaymentText { text: Legacy.Tr.phrase("ĐÃ CÀI · ") + serverBridge.installed.length; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1; color: GlassTheme.muted }
                }
            }
            Component {
                id: installedRow
                Glass {
                    property var installedData: resultRow.modelData.installed
                    width: resultRow.width; padding: 14; implicitHeight: installedBody.implicitHeight + 28
                    Column {
                        id: installedBody; width: parent.width; spacing: 10
                        PaymentText { width: parent.width; text: installedData.file_name; wrapMode: Text.WrapAnywhere; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: installedData.content_kind + " · " + (installedData.source === "manual" ? Legacy.Tr.phrase("File chép tay") : installedData.source + " · " + installedData.version_id); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                        Button { objectName: "serverContentRemove-" + installedData.file_name; label: Legacy.Tr.phrase("Gỡ"); quiet: true; clickable: root.writable; onClicked: { var kind = installedData.content_kind; var fileName = installedData.file_name; confirmDialog.ask(Legacy.Tr.phrase("Gỡ ") + fileName + "?", Legacy.Tr.phrase("File được chuyển vào .nostalgia/removed trong thư mục server để bạn có thể lấy lại."), function() { serverBridge.removeContent(kind, fileName); }); } }
                    }
                }
            }
        }
    }
    Controls.Popup {
        id: versionPopup
        objectName: "serverContentVersionDialog"
        parent: Controls.Overlay.overlay
        width: Math.min(540 * GlassTheme.scale, parent ? parent.width - 40 : 540)
        height: Math.min(versionBody.implicitHeight + 48, parent ? parent.height - 40 : 480)
        x: parent ? (parent.width - width) / 2 : 0; y: parent ? (parent.height - height) / 2 : 0
        modal: true; dim: true; focus: true; padding: 24
        closePolicy: serverBridge.busy ? Controls.Popup.NoAutoClose : Controls.Popup.CloseOnEscape
        background: PopupGlass {}
        Controls.Overlay.modal: Rectangle { color: "#99080b12" }
        contentItem: InertialScroll {
            contentHeight: versionBody.implicitHeight
            Column { id: versionBody; width: parent.width; spacing: 14
                Row { width: parent.width; spacing: 10
                    PaymentText { width: parent.width - closeVersion.width - 10; text: Legacy.Tr.phrase("Chọn bản tương thích"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
                    Button { id: closeVersion; width: 38; label: "×"; quiet: true; clickable: !serverBridge.busy; Accessible.name: Legacy.Tr.phrase("Đóng chọn phiên bản nội dung server"); onClicked: versionPopup.close() }
                }
                PaymentText { width: parent.width; text: root.projectId + " · Minecraft " + (serverBridge.selected.game_version || ""); color: GlassTheme.muted; wrapMode: Text.WrapAnywhere }
                Select { objectName: "serverContentVersion"; width: parent.width; model: serverBridge.contentVersions.map(function(v) { return v.title; }); currentIndex: -1; displayText: root.versionId ? (serverBridge.contentVersions.filter(function(v) { return v.version_id === root.versionId; })[0] || {}).title || "" : Legacy.Tr.phrase("Chọn bản phát hành…"); enabled: !serverBridge.busy; onActivated: function(i) { root.versionId = serverBridge.contentVersions[i].version_id; } }
                PaymentText { width: parent.width; text: serverBridge.busy ? Legacy.Tr.message(serverBridge.activity) : serverBridge.contentVersions.length ? Legacy.Tr.phrase("Dependency bắt buộc trên Modrinth được kiểm tra và cài cùng. Server cần dừng trước khi đổi nội dung.") : Legacy.Tr.phrase("Không có bản tải trực tiếp phù hợp. Kiểm tra loader hoặc dependency trên trang dự án."); color: GlassTheme.muted }
                PaymentText { width: parent.width; text: Legacy.Tr.message(serverBridge.note); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                Button { objectName: "serverContentInstall"; label: Legacy.Tr.phrase("Cài lên server"); primary: true; clickable: root.writable && !!root.versionId; onClicked: serverBridge.installContent(root.source, root.kind, root.projectId, root.versionId) }
            }
        }
    }
    Connections { target: serverBridge; function onContentInstalled() { versionPopup.close(); } }
}
