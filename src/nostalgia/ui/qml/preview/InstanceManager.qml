import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    objectName: "modernInstanceManager"
    parent: Controls.Overlay.overlay
    width: Math.min(880, parent ? parent.width - 40 : 880)
    height: Math.min(700, parent ? parent.height - 40 : 700)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24; modal: true; dim: true; focus: true
    property var instance: ({})
    property int section: 0
    readonly property bool writable: !bridge.gameRunning && !bridge.storageBusy && !bridge.busy
    signal repairRequested(var instance)
    signal exportRequested(var instance)
    property bool exportingAfterClose: false
    onClosed: { if (exportingAfterClose) { exportingAfterClose = false; exportRequested(instance); } }
    function openFor(entry) {
        instance = entry; section = 0;
        nameField.text = entry.label || "";
        groupField.text = entry.groupName || "";
        heapField.text = entry.maxHeapMegabytes ? String(entry.maxHeapMegabytes) : "";
        widthField.text = entry.windowWidth ? String(entry.windowWidth) : "";
        heightField.text = entry.windowHeight ? String(entry.windowHeight) : "";
        favorite.checked = entry.favorite === true;
        deleteExternal.checked = false;
        contentBridge.selectInstance(entry.instanceId);
        open();
    }
    function save() {
        bridge.updateInstance(instance.instanceId, nameField.text, parseInt(heapField.text) || 0, parseInt(widthField.text) || 0, parseInt(heightField.text) || 0);
        storageBridge.setOrganization(instance.instanceId, groupField.text, favorite.checked);
        close();
    }
    background: PopupGlass {}
    Controls.Overlay.modal: Rectangle { color: "#aa080b12" }
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal }
        }
    }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: GlassTheme.quick } }
    InstanceLibraryDialog {
        id: addContent
        onClosed: {
            if (installedPanel.item) installedPanel.item.refresh();
            Qt.callLater(function() { addContentButton.forceActiveFocus(); });
        }
    }
    contentItem: Item {
        Column {
            id: header
            width: parent.width - 46; spacing: 8
            PaymentText { width: parent.width; text: root.instance.label || Legacy.Tr.phrase("Bản chơi"); font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold; elide: Text.ElideRight; maximumLineCount: 1; font.family: GlassTheme.displayFont }
            PaymentText { width: parent.width; text: "Minecraft · " + (root.instance.versionId || ""); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontLabel }
        }
        Button { anchors.right: parent.right; width: 38; label: "×"; quiet: true; Accessible.name: Legacy.Tr.phrase("Đóng quản lý bản chơi"); onClicked: root.close() }
        MotionTabs { id: tabs; anchors.top: header.bottom; anchors.topMargin: 20; width: parent.width; labels: [Legacy.Tr.phrase("Tổng quan"), Legacy.Tr.phrase("Nội dung đã cài"), Legacy.Tr.phrase("Hiệu năng"), Legacy.Tr.phrase("Xuất & dữ liệu")]; currentIndex: root.section; namePrefix: "instanceSection-"; onSelected: function(index) { root.section = index; } }
        Row {
            id: footer
            anchors.right: parent.right; anchors.bottom: parent.bottom; spacing: 8
            GuideButton { topicId: root.section === 3 ? "backup" : "library" }
            Button { id: addContentButton; objectName: "instanceAddContent"; visible: root.section === 1; label: Legacy.Tr.phrase("Thêm nội dung  +"); primary: true; clickable: root.writable && !contentBridge.busy && !projectBridge.installing; onClicked: addContent.openFor(root.instance, installedPanel.item ? installedPanel.item.kind : "mod") }
            Button { label: Legacy.Tr.phrase("Mở thư mục"); quiet: true; onClicked: bridge.openInstanceFolder(root.instance.instanceId) }
            Button { objectName: "instanceSave"; visible: root.section === 0 || root.section === 2; label: Legacy.Tr.phrase("Lưu thay đổi"); primary: true; clickable: root.writable; onClicked: root.save() }
        }
        InertialScroll {
            id: formScroll
            objectName: "instanceManagerScroll"
            visible: root.section !== 1
            anchors.top: tabs.bottom; anchors.topMargin: 20; anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: footer.top; anchors.bottomMargin: 20
            contentHeight: form.implicitHeight + 8
            Column {
                id: form
                width: parent.width - 8; spacing: 18
                Column {
                    visible: root.section === 0
                    width: parent.width; spacing: 10
                    PaymentText { text: Legacy.Tr.phrase("Tên bản chơi"); font.weight: Font.DemiBold }
                    Input { id: nameField; objectName: "instanceName"; width: parent.width; placeholder: Legacy.Tr.phrase("Tên hiển thị") }
                    PaymentText { text: Legacy.Tr.phrase("Nhóm"); color: GlassTheme.muted }
                    Input { id: groupField; width: parent.width; placeholder: Legacy.Tr.phrase("Sinh tồn, modpack, chơi cùng bạn…") }
                    Row { spacing: 12; Legacy.Toggle { id: favorite; accessibleLabel: Legacy.Tr.phrase("Ghim bản chơi"); onToggled: function(value) { checked = value; } } PaymentText { text: Legacy.Tr.phrase("Ghim bản chơi lên đầu danh sách"); anchors.verticalCenter: parent.verticalCenter } }
                    Glass {
                        width: parent.width; height: folderNote.implicitHeight + 32; padding: 16
                        PaymentText { id: folderNote; width: parent.width; text: Legacy.Tr.phrase("Thư mục chơi\n") + (root.instance.gameDir || ""); color: GlassTheme.muted; wrapMode: Text.WrapAnywhere }
                    }
                }
                Column {
                    visible: root.section === 2
                    width: parent.width; spacing: 12
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Để trống để sử dụng thiết lập mặc định của launcher."); color: GlassTheme.muted }
                    PaymentText { text: Legacy.Tr.phrase("Bộ nhớ tối đa · MB"); font.weight: Font.DemiBold }
                    Input { id: heapField; objectName: "instanceHeap"; width: parent.width; placeholder: Legacy.Tr.phrase("Mặc định") }
                    PaymentText { text: Legacy.Tr.phrase("Kích thước cửa sổ game"); font.weight: Font.DemiBold }
                    Flow { width: parent.width; spacing: 12; Input { id: widthField; width: Math.min(240, form.width); placeholder: Legacy.Tr.phrase("Chiều rộng · px") } Input { id: heightField; width: Math.min(240, form.width); placeholder: Legacy.Tr.phrase("Chiều cao · px") } }
                }
                Column {
                    visible: root.section === 3
                    width: parent.width; spacing: 14
                    PaymentText { text: Legacy.Tr.phrase("Đóng gói & dữ liệu"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold; font.family: GlassTheme.displayFont }
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Xuất MRPACK hoặc ZIP để chia sẻ và nhập lại. Bạn có thể chọn đóng gói cả thế giới đã chơi."); color: GlassTheme.muted }
                    Flow { width: parent.width; spacing: 8; Button { objectName: "instanceExport"; label: Legacy.Tr.phrase("Xuất modpack…"); clickable: root.writable; onClicked: { root.exportingAfterClose = true; root.close(); } } Button { label: Legacy.Tr.phrase("Kiểm tra xung đột mod"); clickable: root.writable; onClicked: { root.close(); root.repairRequested(root.instance); } } }
                    Glass {
                        width: parent.width; height: deleteColumn.implicitHeight + 32; padding: 16
                        Column { id: deleteColumn; width: parent.width; spacing: 12
                            PaymentText { id: trashNote; width: parent.width; text: Legacy.Tr.phrase("Xóa vĩnh viễn\nMods, cấu hình và thế giới trong thư mục do launcher quản lý sẽ bị xóa. Không thể hoàn tác."); color: GlassTheme.muted }
                            Row { visible: root.instance.customGameDir === true; width: parent.width; spacing: 12
                                Legacy.Toggle { id: deleteExternal; objectName: "deleteExternalGameDir"; enabled: root.writable; accessibleLabel: Legacy.Tr.phrase("Xóa cả thư mục game riêng"); onToggled: function(value) { checked = value; } }
                                PaymentText { width: parent.width - deleteExternal.width - 12; text: Legacy.Tr.phrase("Xóa cả thư mục game riêng"); anchors.verticalCenter: parent.verticalCenter }
                            }
                            Button { id: trashButton; objectName: "instanceTrash"; label: Legacy.Tr.phrase("Xóa vĩnh viễn"); danger: true; quiet: true; clickable: root.writable; onClicked: { var instanceId = root.instance.instanceId; var eraseExternal = root.instance.customGameDir === true && deleteExternal.checked; confirmDialog.ask(Legacy.Tr.phrase("Xóa vĩnh viễn ") + root.instance.label + "?", root.instance.customGameDir ? (eraseExternal ? Legacy.Tr.phrase("Xóa toàn bộ mods, cấu hình và thế giới tại: ") : Legacy.Tr.phrase("Gỡ bản chơi khỏi launcher. Giữ lại thư mục game riêng: ")) + root.instance.gameDir + (eraseExternal ? Legacy.Tr.phrase("\nKhông thể hoàn tác.") : "") : Legacy.Tr.phrase("Toàn bộ mods, cấu hình và thế giới của bản chơi sẽ bị xóa. Không thể hoàn tác. Bạn có thể xuất modpack trước khi xóa."), function() { storageBridge.deletePermanently(instanceId, eraseExternal); root.close(); }); } }
                        }
                    }
                }
            }
        }
        Loader {
            id: installedPanel
            anchors.top: tabs.bottom; anchors.topMargin: 20; anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: footer.top; anchors.bottomMargin: 20
            active: root.opened && root.section === 1
            visible: active
            sourceComponent: Component { InstalledContent { chooseInstance: false } }
        }
    }
}
