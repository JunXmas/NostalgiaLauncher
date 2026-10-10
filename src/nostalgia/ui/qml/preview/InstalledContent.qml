import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "modernInstalledContent"
    property string kind: "mod"
    property bool chooseInstance: true
    readonly property bool writable: !!contentBridge.instanceId && !contentBridge.busy && !bridge.gameRunning && !bridge.storageBusy
    function refresh() {
        contentBridge.setKind(kind);
        if (contentBridge.instanceId) contentBridge.refreshInstalled(kind);
    }
    Component.onCompleted: {
        if (!contentBridge.instanceId && bridge.instances.length) contentBridge.selectInstance(bridge.instances[0].instanceId);
        refresh();
    }
    onKindChanged: refresh()
    Connections {
        target: contentBridge
        function onTargetChanged() { root.refresh(); }
    }
    Column {
            id: contents
            width: parent.width - 8; spacing: 14
            Flow {
                id: toolbar
                width: parent.width; spacing: 10
                Select {
                    visible: root.chooseInstance
                    width: Math.min(260, root.width)
                    model: bridge.instances.map(function (entry) { return entry.label; })
                    currentIndex: bridge.instances.findIndex(function (entry) { return entry.instanceId === contentBridge.instanceId; })
                    onActivated: function(index) { contentBridge.selectInstance(bridge.instances[index].instanceId); }
                }
                Input {
                    objectName: "installedSearch"
                    width: Math.min(260, root.width); height: 42
                    placeholder: Legacy.Tr.phrase("Tìm trong nội dung đã cài…")
                    onTextChanged: contentBridge.setInstalledFilter(text)
                    Component.onDestruction: contentBridge.setInstalledFilter("")
                }
                Button { label: Legacy.Tr.phrase("Kiểm tra cập nhật"); clickable: root.writable && !contentBridge.identifying; onClicked: contentBridge.checkUpdates(root.kind) }
                Button { label: contentBridge.identifying ? Legacy.Tr.phrase("Đang nhận diện…") : Legacy.Tr.phrase("Nhận diện lại"); quiet: true; clickable: root.writable && !contentBridge.identifying; onClicked: contentBridge.identifyInstalled(root.kind) }
            }
            Flow {
                id: kinds
                width: parent.width; spacing: 6
                Repeater {
                    model: [{key: "mod", label: "Mod"}, {key: "resourcepack", label: Legacy.Tr.phrase("Resource pack")}, {key: "shader", label: "Shader"}]
                    Button {
                        label: modelData.label; selected: root.kind === modelData.key; quiet: true; height: 36
                        onClicked: root.kind = modelData.key
                    }
                }
            }
            PaymentText {
                id: summary
                width: parent.width
                text: !contentBridge.instanceId ? Legacy.Tr.phrase("Chọn bản chơi để quản lý nội dung đã cài.") : bridge.gameRunning ? Legacy.Tr.phrase("Đóng game trước khi thay đổi nội dung.") : contentBridge.installedShownCount + " / " + contentBridge.installed.length + Legacy.Tr.phrase(" file · bật, tắt và cập nhật tại đây")
                color: GlassTheme.muted
            }
            InertialList {
                id: rows
                objectName: "installedScroll"
                width: parent.width
                height: Math.max(1, root.height - toolbar.height - kinds.height - summary.height - 42)
                spacing: 12
                model: contentBridge.installedModel
                delegate: Legacy.InstalledCard {
                    required property var model
                    artworkEnabled: rows.visible && y + height >= rows.contentY && y <= rows.contentY + rows.height
                    objectName: "installedCard-" + model.fileName
                    width: rows.width
                    installedContent: model
                    toggleable: root.kind === "mod"
                    enabled: root.writable
                    ListView.onReused: confirmingRemove = false
                    onToggled: function(filename, checked) { contentBridge.setEnabled(root.kind, filename, checked); }
                    onUpdateRequested: function(filename) { contentBridge.updateInstalled(root.kind, filename); }
                    onRemoveRequested: function(filename) { contentBridge.remove(root.kind, filename); }
                }
                footer: Item {
                    width: rows.width; height: rows.count ? 16 : empty.implicitHeight + 48
                    Glass {
                        width: parent.width; height: parent.height; visible: !rows.count
                        PaymentText { id: empty; width: parent.width; text: contentBridge.installed.length ? Legacy.Tr.phrase("Không tìm thấy file phù hợp.") : Legacy.Tr.phrase("Nội dung của bản chơi sẽ xuất hiện ở đây. Bạn có thể thêm mod, shader và resource pack từ thư viện."); color: GlassTheme.muted }
                    }
                }
            }
    }
}
