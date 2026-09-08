import QtQuick
import QtQuick.Dialogs
import "../"

/* Trang BẢN CHƠI: lưới thẻ, nút tạo mới mở hộp thoại hai cột, gỡ bằng nút trên thẻ.
   Kéo một file .mrpack / .zip từ máy thả vào bất kỳ đâu trên trang là nhập modpack. */
Item {
    id: page
    objectName: "instancesPage"
    signal navigate(int pageIndex)
    readonly property var packSuffixes: [".mrpack", ".zip"]

    function isPackUrl(url) {
        var lower = String(url).toLowerCase();
        return page.packSuffixes.some(function (suffix) { return lower.endsWith(suffix); });
    }
    // Nhận danh sách URL vừa thả; chỉ nhập MỘT modpack (nhập song song là hai việc nền giẫm
    // nhau). Trả về số file modpack tìm thấy để lớp phủ nói đúng chuyện gì đã xảy ra.
    function importDropped(urls) {
        var packs = [];
        for (var index = 0; index < urls.length; index++)
            if (page.isPackUrl(urls[index])) packs.push(String(urls[index]));
        if (packs.length > 0) contentBridge.importModpackFile(packs[0], "");
        return packs.length;
    }

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 66
        Column {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            spacing: 3
            Text { text: "Bản chơi"; color: Theme.text; font.pixelSize: 24; font.bold: true }
            Text {
                text: bridge.instances.length + " bản chơi  ·  mỗi bản một thư mục riêng, kho tải dùng chung"
                color: Theme.textMuted; font.pixelSize: 12
            }
        }
        Row {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            spacing: 8
            ActionButton {
                primary: false
                label: "Nhập modpack từ file"
                clickable: !bridge.busy && !contentBridge.busy
                onClicked: packPicker.open()
            }
            ActionButton {
                label: "+  Tạo mới"
                onClicked: dialog.openDialog()
            }
        }
    }

    Panel {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: 0 }

        Text {
            visible: bridge.instances.length === 0
            text: "Chưa có bản chơi nào. Bấm “Tạo mới” để chọn phiên bản và loader."
            color: Theme.textMuted; font.pixelSize: 12
        }

        Grid {
            id: grid
            anchors { left: parent.left; right: parent.right; top: parent.top }
            readonly property int cardHeight: 168
            columns: 4
            spacing: Theme.gap
            Repeater {
                model: bridge.instances
                InstanceCard {
                    width: Math.floor((grid.width - (grid.columns - 1) * Theme.gap) / grid.columns)
                    height: grid.cardHeight
                    label: modelData.label
                    versionId: modelData.versionId
                    playtimeText: modelData.playtimeText; launchCount: modelData.launchCount
                    worldCount: modelData.worldCount; modCount: modelData.modCount
                    removable: true
                    editable: true
                    iconUrl: modelData.iconUrl || ""
                    playable: bridge.activePlayerName.length > 0 && !bridge.busy
                    onPlayRequested: bridge.play(modelData.instanceId)
                    onRemoveRequested: bridge.removeInstance(modelData.instanceId)
                    onEditRequested: editDialog.openFor(modelData)
                }
            }
        }
    }

    // Vùng nhận thả phủ cả trang; chỉ sáng lên khi thứ đang kéo là file modpack.
    DropArea {
        id: dropZone
        objectName: "packDropArea"
        anchors.fill: parent
        // `urls` chỉ có trên sự kiện kéo (DragEvent), không có trên `DropArea.drag`, nên trạng
        // thái "đang giữ modpack" phải cập nhật theo sự kiện vào / ra / thả.
        property bool holdingPack: false
        function hasPackUrls(urls) {
            if (!urls) return false;
            for (var index = 0; index < urls.length; index++) if (page.isPackUrl(urls[index])) return true;
            return false;
        }
        onEntered: function (drag) {
            dropZone.holdingPack = dropZone.hasPackUrls(drag.urls);
            if (!dropZone.holdingPack) drag.accepted = false;
        }
        onExited: dropZone.holdingPack = false
        onDropped: function (drop) {
            dropZone.holdingPack = false;
            if (page.importDropped(drop.urls) > 0) drop.accept();
        }
        Rectangle {
            anchors.fill: parent
            visible: dropZone.holdingPack
            color: "#cc0b120d"
            border.color: Theme.accent; border.width: 2; radius: Theme.radius
            Column {
                anchors.centerIn: parent; spacing: 8
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "⤓"; color: Theme.accent; font.pixelSize: 40 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Thả để nhập modpack"; color: Theme.text; font.pixelSize: 18; font.bold: true }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: ".mrpack (Modrinth) hoặc .zip (CurseForge) — tạo thành một bản chơi mới"; color: Theme.textMuted; font.pixelSize: 12 }
            }
        }
    }

    CreateInstanceDialog { id: dialog; objectName: "createDialog"; anchors.fill: parent }
    InstanceEditDialog { id: editDialog; anchors.fill: parent }

    // Modpack từ file trên máy: .mrpack (Modrinth) hoặc .zip (CurseForge); nhận dạng theo nội dung.
    FileDialog {
        id: packPicker
        title: "Chọn modpack"
        nameFilters: ["Modpack (*.mrpack *.zip)", "Mọi file (*)"]
        onAccepted: contentBridge.importModpackFile(selectedFile.toString(), "")
    }
}
