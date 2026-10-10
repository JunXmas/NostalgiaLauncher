import QtQuick
import QtQuick.Window
import "../" as Legacy

Item {
    id: root
    objectName: "minimalLibrary"
    property bool installedMode: false
    property string kind: "modpack"
    property string sort: "relevance"
    property bool instanceScoped: false
    property string instanceLabel: ""
    readonly property bool compactScope: instanceScoped && height < 550 * GlassTheme.scale
    signal advancedRequested
    readonly property var kinds: [
        {
            label: "Modpack",
            key: "modpack"
        },
        {
            label: "Mod",
            key: "mod"
        },
        {
            label: "Shader",
            key: "shader"
        },
        {
            label: Legacy.Tr.phrase("Gói tài nguyên"),
            key: "resourcepack"
        }
    ].filter(function(choice) { return !root.instanceScoped || choice.key !== "modpack"; })
    function refresh() {
        contentBridge.setKind(root.kind);
        if (root.instanceScoped && contentBridge.instanceId) contentBridge.refreshInstalled(root.kind);
        contentBridge.search(root.kind, search.text, root.sort);
    }
    Component.onCompleted: refresh()
    Timer {
        id: debounce
        interval: 300
        onTriggered: root.refresh()
    }
    Item {
        id: header
        width: parent.width
        height: Math.max(root.compactScope ? 64 : 86, heading.implicitHeight + 16)
        Column {
            id: heading
            width: parent.width - sourcePicker.width - 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: root.instanceScoped ? Legacy.Tr.phrase("Thêm nội dung") : Legacy.Tr.phrase("Khám phá")
                color: GlassTheme.text
                font.family: GlassTheme.displayFont
                font.pixelSize: root.compactScope ? GlassTheme.fontSection : GlassTheme.fontPage
                font.weight: Font.DemiBold
            }
            Text {
                objectName: "libraryTargetNote"
                width: parent.width; wrapMode: Text.WordWrap
                text: root.instanceScoped ? root.instanceLabel + " · Minecraft " + contentBridge.gameVersion + " · " + contentBridge.loaderKind + (root.compactScope ? "" : Legacy.Tr.phrase("\nChỉ cài vào bản chơi này; phiên bản tương thích được lọc sẵn.")) : Legacy.Tr.phrase("Một thế giới quen thuộc. Những cách chơi mới.")
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: root.compactScope ? GlassTheme.fontNote : GlassTheme.fontBody
            }
        }
        Select {
            id: sourcePicker
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 145 * GlassTheme.scale
            model: ["Modrinth", "CurseForge"]
            currentIndex: contentBridge.source === "curseforge" ? 1 : 0
            onActivated: function (index) {
                contentBridge.setSource(index ? "curseforge" : "modrinth");
                root.refresh();
            }
        }
    }
    Flow {
        id: types
        width: parent.width
        anchors.top: header.bottom
        anchors.topMargin: 8
        spacing: 8
        Repeater {
            model: root.kinds
            Button {
                objectName: "libraryKind-" + modelData.key
                visible: !root.installedMode
                label: modelData.label
                selected: root.kind === modelData.key
                quiet: true
                onClicked: {
                    root.kind = modelData.key;
                    root.refresh();
                }
            }
        }
        Button {
            objectName: "openModernInstalled"
            visible: !root.instanceScoped
            label: root.installedMode ? Legacy.Tr.phrase("Duyệt thư viện") : Legacy.Tr.phrase("Đã cài")
            selected: root.installedMode
            quiet: true
            onClicked: root.installedMode = !root.installedMode
        }
        GuideButton { topicId: "library" }
    }
    Item {
        id: filters
        visible: !root.installedMode
        anchors.top: types.bottom
        anchors.topMargin: root.compactScope ? 12 : 24
        width: parent.width
        height: 46 * GlassTheme.scale
        Input {
            id: search
            objectName: "minimalLibrarySearch"
            anchors.left: parent.left
            anchors.right: sortPicker.left
            anchors.rightMargin: 12
            placeholder: Legacy.Tr.phrase("Tìm điều mới mẻ cho thế giới của bạn…")
            onTextChanged: debounce.restart()
        }
        Select {
            id: sortPicker
            anchors.right: parent.right
            width: 170 * GlassTheme.scale
            model: [Legacy.Tr.phrase("Phù hợp nhất"), Legacy.Tr.phrase("Nhiều lượt tải"), Legacy.Tr.phrase("Mới nhất")]
            onActivated: function (index) {
                root.sort = ["relevance", "downloads", "newest"][index];
                root.refresh();
            }
        }
    }
    Item {
        id: status
        visible: !root.installedMode
        anchors.top: filters.bottom
        anchors.topMargin: root.compactScope ? 10 : 18
        width: parent.width
        height: 26
        Text {
            text: contentBridge.searching ? Legacy.Tr.phrase("Đang tìm kiếm…") : contentBridge.totalHits.toLocaleString(Qt.locale(Legacy.Tr.localeName), 'f', 0) + Legacy.Tr.plural(" kết quả", contentBridge.totalHits)
            color: GlassTheme.muted
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontNote
        }
        Button {
            anchors.right: parent.right
            visible: !root.instanceScoped
            height: 24
            label: Legacy.Tr.phrase("Bộ lọc nâng cao  ↗")
            quiet: true
            onClicked: advanced.open()
        }
    }
    InertialGrid {
        id: libraryViewport
        objectName: "libraryScroll"
        visible: !root.installedMode
        anchors.top: status.bottom; anchors.topMargin: 12
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        readonly property int columns: root.compactScope ? 1 : Math.max(1, Math.floor((width + 8) / (300 * GlassTheme.scale)))
        cellWidth: Math.max(1, Math.floor((width - 8) / columns))
        cellHeight: (root.compactScope ? 126 : 218) * GlassTheme.scale + 16
        model: contentBridge.resultsModel
        delegate: Item {
            required property var model
            width: libraryViewport.cellWidth; height: libraryViewport.cellHeight
            ProjectTile {
                width: parent.width - 16; height: parent.height - 16
                project: parent.model; compactScope: root.compactScope; contentKind: root.kind; instanceScoped: root.instanceScoped
                artworkEnabled: libraryViewport.visible && parent.y + parent.height >= libraryViewport.contentY && parent.y <= libraryViewport.contentY + libraryViewport.height
                onModpackRequested: function(projectId, title) { pack.openFor(projectId, title); }
            }
        }
        footer: Column {
            width: libraryViewport.width - 8; spacing: 16; bottomPadding: 20
            PaymentText {
                width: parent.width
                visible: !contentBridge.searching && !libraryViewport.count
                text: Legacy.Tr.phrase("Chưa có kết quả. Thử đổi từ khóa hoặc nguồn nội dung.")
                color: GlassTheme.muted
            }
            Button {
                visible: contentBridge.hasMore
                anchors.horizontalCenter: parent.horizontalCenter
                label: contentBridge.searching ? Legacy.Tr.phrase("Đang tải…") : Legacy.Tr.phrase("Xem thêm")
                clickable: !contentBridge.searching
                onClicked: contentBridge.loadMore()
            }
        }
    }
    Loader {
        anchors.top: types.bottom; anchors.topMargin: 24
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        active: root.installedMode
        sourceComponent: Component { InstalledContent {} }
    }
    LibraryFilters { id: advanced; kind: root.kind; onApplied: root.refresh() }
    Legacy.ModpackDialog {
        id: pack
        objectName: "modernQuickModpack"
        parent: root.Window.window ? root.Window.window.contentItem : root
        anchors.fill: parent
    }
}
