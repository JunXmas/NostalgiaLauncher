import QtQuick

/*
  Hàng lọc của thư viện nội dung: ba ô cùng một dòng — LOADER, PHIÊN BẢN (cả hai chọn nhiều,
  thu gọn trong `FilterChip`) và SẮP XẾP (chọn một, dùng `Dropdown` có sẵn).

  Trước đây đây là một cột dọc 210px trải thẳng mọi lựa chọn: 4 loader cộng hàng chục phiên
  bản game đẩy phần sắp xếp ra khỏi tầm mắt, và danh mục phiên bản phải cắt còn 60 mục cho
  vừa cột. Gói lại thành ô thì khay bên trong cuộn được nên không cắt gì, và phần kết quả
  lấy lại được cả bề ngang.

  Trạng thái lọc sống ở contentBridge để đổi trang quay lại vẫn còn.
*/
Item {
    id: root
    property bool loadersEnabled: true
    // Modpack tự tạo bản chơi mới nên không có "loader/phiên bản của bản chơi đích" để lọc theo.
    property bool versionsEnabled: true
    property var sortKeys: []
    property var sortLabels: []
    property int sortIndex: 0
    signal changed()

    readonly property var loaderOptions: [
        { value: "fabric", label: "Fabric" },
        { value: "forge", label: "Forge" },
        { value: "neoforge", label: "NeoForge" },
        { value: "quilt", label: "Quilt" },
    ]
    readonly property var versionOptions: catalogBridge.releasedVersions.map(function (released) {
        return { value: released.versionId, label: released.versionId };
    })
    readonly property bool singleOnly: contentBridge.source === "curseforge"

    Component.onCompleted: if (catalogBridge.releasedVersions.length === 0) catalogBridge.loadReleasedVersions()

    height: 32 + (hint.visible ? hint.height + 6 : 0)

    Row {
        id: chips
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: 32
        spacing: 8

        FilterChip {
            id: loaderChip
            objectName: "loaderChip"
            width: 168
            visible: root.loadersEnabled
            title: Tr.phrase("Mọi loader")
            options: root.loaderOptions
            selected: contentBridge.selectedLoaders
            onToggled: function (value, checked) { contentBridge.setLoaderSelected(value, checked); root.changed(); }
            onCleared: { contentBridge.clearLoaders(); root.changed(); }
            onOpenChanged: if (open) { versionChip.open = false; sortBox.open = false; }
        }
        FilterChip {
            id: versionChip
            objectName: "versionChip"
            width: 168
            visible: root.versionsEnabled
            title: Tr.phrase("Mọi phiên bản")
            searchable: true
            searchPlaceholder: Tr.phrase("Tìm phiên bản...")
            emptyNote: catalogBridge.busy ? Tr.phrase("Đang tải danh mục...") : Tr.phrase("Không tải được danh mục phiên bản.")
            options: root.versionOptions
            selected: contentBridge.selectedGameVersions
            onToggled: function (value, checked) { contentBridge.setGameVersionSelected(value, checked); root.changed(); }
            onCleared: { contentBridge.clearGameVersions(); root.changed(); }
            onOpenChanged: if (open) { loaderChip.open = false; sortBox.open = false; }
        }
        Dropdown {
            id: sortBox
            objectName: "sortBox"
            width: 168; height: 32
            placeholder: Tr.phrase("Sắp xếp")
            model: root.sortLabels
            currentIndex: root.sortIndex
            onActivated: function (index) { root.sortIndex = index; root.changed(); }
            onOpenChanged: if (open) { loaderChip.open = false; versionChip.open = false; }
        }
    }
    Text {
        id: hint
        anchors { top: chips.bottom; topMargin: 6; left: parent.left; right: parent.right }
        visible: root.singleOnly && (contentBridge.selectedLoaders.length > 1
                                     || contentBridge.selectedGameVersions.length > 1)
        wrapMode: Text.WordWrap
        text: Tr.phrase("CurseForge chỉ lọc theo loader và phiên bản ĐẦU TIÊN được tick.")
        color: Theme.accent; font.pixelSize: Theme.fontLabel
    }
}
