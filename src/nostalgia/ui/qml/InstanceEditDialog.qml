import QtQuick

/* Sửa một bản chơi: tên hiển thị, RAM, kích thước cửa sổ. Mã bản chơi và phiên bản không đổi
   (đổi phiên bản là tạo bản chơi khác — thế giới và mod gắn với phiên bản). */
Item {
    id: dialog
    objectName: "instanceEditDialog"
    visible: false
    z: 100
    property var instance: ({})

    function openFor(entry) {
        instance = entry;
        nameField.text = entry.label || "";
        heapField.text = entry.maxHeapMegabytes ? String(entry.maxHeapMegabytes) : "";
        widthField.text = entry.windowWidth ? String(entry.windowWidth) : "";
        heightField.text = entry.windowHeight ? String(entry.windowHeight) : "";
        visible = true;
    }
    function save() {
        bridge.updateInstance(instance.instanceId, nameField.text, parseInt(heapField.text) || 0,
                              parseInt(widthField.text) || 0, parseInt(heightField.text) || 0);
        visible = false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 480; height: 356
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        MouseArea { anchors.fill: parent }

        Column {
            anchors { fill: parent; margins: 26 }
            spacing: 12
            Text { text: "Sửa bản chơi"; color: Theme.text; font.pixelSize: 18; font.bold: true }
            Text {
                text: (dialog.instance.instanceId || "") + "  ·  " + (dialog.instance.versionId || "")
                color: Theme.textMuted; font.pixelSize: 11; font.family: "monospace"
            }
            Text {
                width: parent.width; elide: Text.ElideMiddle
                text: "Thư mục chơi: " + (dialog.instance.gameDir || "")
                color: Theme.textMuted; font.pixelSize: 11
            }
            Text { text: "TÊN"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
            TextField { id: nameField; width: parent.width; placeholder: "Tên hiển thị"; onAccepted: dialog.save() }
            Row {
                spacing: 12
                Column {
                    spacing: 6
                    Text { text: "RAM (MB)"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    TextField { id: heapField; width: 130; placeholder: "mặc định" }
                }
                Column {
                    spacing: 6
                    Text { text: "CỬA SỔ RỘNG"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    TextField { id: widthField; width: 130; placeholder: "mặc định" }
                }
                Column {
                    spacing: 6
                    Text { text: "CỬA SỔ CAO"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    TextField { id: heightField; width: 130; placeholder: "mặc định" }
                }
            }
            Item { width: 1; height: 6 }
            Row {
                spacing: 8
                ActionButton { label: "Lưu"; onClicked: dialog.save() }
                ActionButton { primary: false; label: "Mở thư mục"; onClicked: bridge.openInstanceFolder(dialog.instance.instanceId) }
                ActionButton { primary: false; label: "Huỷ"; onClicked: dialog.visible = false }
            }
        }
    }
}
