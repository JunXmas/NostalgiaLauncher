import QtQuick
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
        if (packs.length > 0) contentBridge.importModpackFile(packs[0], "", "");
        return packs.length;
    }

    Item {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 72 * Theme.textScale
        Column {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            spacing: 3
            PageTitle { caption: Tr.phrase("Bản chơi") }
            Text {
                text: bridge.instances.length + " · " + Tr.phrase("Bản chơi")
                color: Theme.textMuted; font.pixelSize: Theme.fontBody
            }
        }
        Row {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            spacing: 8
            ActionButton {
                primary: false
                label: Tr.phrase("⬇ Nhập bản chơi")
                clickable: !bridge.busy && !importBridge.busy
                onClicked: importDialog.openDialog()
            }
            ActionButton {
                label: Tr.phrase("+  Tạo mới")
                onClicked: dialog.openDialog()
            }
        }
    }

    Column {
        id: filters
        anchors { top: header.bottom; left: parent.left; right: parent.right; margins: Theme.gap; topMargin: 0 }
        spacing: 8
        Flow {
            width: parent.width; spacing: 10
            TextField { id: search; objectName: "instanceSearch"; width: Math.min(300, parent.width); placeholder: Tr.phrase("Tìm bản chơi hoặc nhóm…") }
            Dropdown { id: groups; width: 220; model: page.groupNames; currentIndex: 0; onActivated: function(index) { page.selectedGroup = index ? page.groupNames[index] : ""; } }
            ActionButton { objectName: "dataManagerButton"; primary: false; label: Tr.phrase("Sao lưu & thùng rác"); onClicked: dataManager.openDialog() }
        }
        Text { width: parent.width; wrapMode: Text.WordWrap; visible: page.storageNote.length > 0; text: page.storageNote; color: Theme.accent; font.pixelSize: Theme.fontBody }
    }
    readonly property var groupNames: {
        var names = [Tr.phrase("Tất cả nhóm")];
        bridge.instances.forEach(function(entry) { if (entry.groupName && names.indexOf(entry.groupName) < 0) names.push(entry.groupName); });
        return names;
    }
    property string selectedGroup: ""
    property string storageNote: ""
    readonly property var filteredInstances: {
        var query = search.text.toLowerCase().trim();
        return bridge.instances.filter(function(entry) {
            return (!page.selectedGroup || entry.groupName === page.selectedGroup)
                && (!query || ((entry.label || "") + " " + entry.instanceId + " " + (entry.groupName || "")).toLowerCase().indexOf(query) >= 0);
        }).sort(function(a,b) {
            if (a.favorite !== b.favorite) return a.favorite ? -1 : 1;
            return (a.label || a.instanceId).localeCompare(b.label || b.instanceId);
        });
    }
    Connections { target: storageBridge; function onCompleted(message) { page.storageNote = message; } }
    Panel {
        anchors { top: filters.bottom; left: parent.left; right: parent.right; bottom: parent.bottom; margins: Theme.gap }
        Flickable {
            anchors.fill: parent; clip: true
            contentHeight: grid.height + 12
            boundsBehavior: Flickable.StopAtBounds
            Grid {
                id: grid
                width: parent.width
                columns: Theme.compactUi ? 1 : Math.max(1, Math.floor((width + Theme.gap) / (300 * Theme.textScale + Theme.gap)))
                spacing: Theme.gap
                Repeater {
                    model: page.filteredInstances
                    ManagedInstance {
                        width: Math.floor((grid.width - (grid.columns - 1) * Theme.gap) / grid.columns)
                        height: implicitHeight
                        entry: modelData
                        onEditRequested: function(entry) { editDialog.openFor(entry); }
                    }
                }
                Text {
                    visible: page.filteredInstances.length === 0
                    width: grid.width; wrapMode: Text.WordWrap
                    text: bridge.instances.length === 0 ? Tr.phrase("Chưa có bản chơi nào. Bấm “Tạo mới” để chọn phiên bản và loader.") : Tr.phrase("Không có bản chơi phù hợp.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
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
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "⤓"; color: Theme.accent; font.pixelSize: Theme.fontHero }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: Tr.phrase("Thả để nhập modpack"); color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: Tr.phrase(".mrpack (Modrinth) hoặc .zip (CurseForge) — tạo thành một bản chơi mới"); color: Theme.textMuted; font.pixelSize: Theme.fontBody }
            }
        }
    }

    DataManager { id: dataManager; anchors.fill: parent }
    CreateInstanceDialog { id: dialog; objectName: "createDialog"; anchors.fill: parent }
    InstanceEditDialog { id: editDialog; anchors.fill: parent }
    ImportInstanceDialog { id: importDialog; objectName: "importDialog"; anchors.fill: parent }
}
