import QtQuick
import QtQuick.Controls as Controls

/* Sửa một bản chơi: tên hiển thị, RAM, kích thước cửa sổ. Mã bản chơi và phiên bản không đổi
   (đổi phiên bản là tạo bản chơi khác — thế giới và mod gắn với phiên bản). */
Item {
    id: dialog
    objectName: "instanceEditDialog"
    visible: false
    z: 100
    Keys.onEscapePressed: visible = false
    property var instance: ({})
    signal repairRequested(var instance)

    function openFor(entry) {
        instance = entry;
        nameField.text = entry.label || "";
        heapField.text = entry.maxHeapMegabytes ? String(entry.maxHeapMegabytes) : "";
        widthField.text = entry.windowWidth ? String(entry.windowWidth) : "";
        heightField.text = entry.windowHeight ? String(entry.windowHeight) : "";
        groupField.text = entry.groupName || "";
        favoriteToggle.checked = entry.favorite === true;
        visible = true;
        nameField.focusInput();
    }
    function save() {
        bridge.updateInstance(instance.instanceId, nameField.text, parseInt(heapField.text) || 0,
                              parseInt(widthField.text) || 0, parseInt(heightField.text) || 0);
        storageBridge.setOrganization(instance.instanceId, groupField.text, favoriteToggle.checked);
        visible = false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    Rectangle {
        anchors.centerIn: parent
        width: Math.min(560, parent.width - 48); height: Math.min(490, parent.height - 32)
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        MouseArea { anchors.fill: parent }

        Controls.ScrollView {
            anchors { fill: parent; margins: 26 }
            clip: true; contentWidth: availableWidth
        Column {
            width: parent.width
            spacing: 12
            Text { text: Tr.phrase("Sửa bản chơi"); color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true }
            Text {
                text: (dialog.instance.instanceId || "") + "  ·  " + (dialog.instance.versionId || "")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody; font.family: "monospace"
            }
            Text {
                width: parent.width; elide: Text.ElideMiddle
                text: Tr.phrase("Thư mục chơi: ") + (dialog.instance.gameDir || "")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody
            }
            Text { text: Tr.phrase("TÊN"); color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
            TextField { id: nameField; width: parent.width; placeholder: Tr.phrase("Tên hiển thị"); onAccepted: dialog.save() }
            Row {
                spacing: 12
                Column {
                    spacing: 6
                    Text { text: "RAM (MB)"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                    TextField { id: heapField; width: 130; placeholder: Tr.phrase("mặc định") }
                }
                Column {
                    spacing: 6
                    Text { text: "CỬA SỔ RỘNG"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                    TextField { id: widthField; width: 130; placeholder: Tr.phrase("mặc định") }
                }
                Column {
                    spacing: 6
                    Text { text: "CỬA SỔ CAO"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                    TextField { id: heightField; width: 130; placeholder: Tr.phrase("mặc định") }
                }
            }
            Text { text: Tr.phrase("Nhóm bản chơi"); color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
            TextField { id: groupField; width: parent.width; placeholder: Tr.phrase("Ví dụ: Sinh tồn, Modpack, Chơi cùng bạn") }
            Row {
                spacing: 12
                Toggle { id: favoriteToggle; accessibleLabel: Tr.phrase("Ghim bản chơi"); onToggled: function(value) { checked = value; } }
                Text { text: Tr.phrase("Ghim bản chơi"); color: Theme.text; font.pixelSize: Theme.fontBody; anchors.verticalCenter: parent.verticalCenter }
            }
            Item { width: 1; height: 6 }
            Flow {
                width: parent.width; spacing: 8
                ActionButton { label: Tr.phrase("Lưu"); onClicked: dialog.save() }
                ActionButton { primary: false; label: Tr.phrase("Mở thư mục"); onClicked: bridge.openInstanceFolder(dialog.instance.instanceId) }
                ActionButton { primary: false; label: Tr.phrase("Huỷ"); onClicked: dialog.visible = false }
            }
            Flow {
                width: parent.width; spacing: 8
                ActionButton { primary: false; label: "Kiểm tra mod"; visible: typeof modRepairBridge !== "undefined"; clickable: !bridge.gameRunning && !bridge.storageBusy; onClicked: dialog.repairRequested(dialog.instance) }
                ActionButton { primary: false; label: Tr.phrase("Sao lưu"); clickable: !storageBridge.busy && !bridge.gameRunning; onClicked: storageBridge.backup(dialog.instance.instanceId) }
                ActionButton {
                    primary: false; label: Tr.phrase("Chuyển vào thùng rác"); clickable: !storageBridge.busy && !bridge.gameRunning
                    onClicked: confirmDialog.ask(Tr.phrase("Chuyển bản chơi vào thùng rác?"), Tr.phrase("Có thể khôi phục trong Sao lưu & thùng rác. Dữ liệu ở thư mục riêng vẫn được giữ nguyên."), function() { storageBridge.moveToTrash(dialog.instance.instanceId); dialog.visible = false; })
                }
            }
        }
        }
    }
}
