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
            label: "Gói tài nguyên",
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
                text: root.instanceScoped ? "Thêm nội dung" : "Khám phá"
                color: GlassTheme.text
                font.family: GlassTheme.displayFont
                font.pixelSize: root.compactScope ? GlassTheme.fontSection : GlassTheme.fontPage
                font.weight: Font.DemiBold
            }
            Text {
                objectName: "libraryTargetNote"
                width: parent.width; wrapMode: Text.WordWrap
                text: root.instanceScoped ? root.instanceLabel + " · Minecraft " + contentBridge.gameVersion + " · " + contentBridge.loaderKind + (root.compactScope ? "" : "\nChỉ cài vào bản chơi này; phiên bản tương thích được lọc sẵn.") : "Một thế giới quen thuộc. Những cách chơi mới."
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
            label: root.installedMode ? "Duyệt thư viện" : "Đã cài"
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
            placeholder: "Tìm điều mới mẻ cho thế giới của bạn…"
            onTextChanged: debounce.restart()
        }
        Select {
            id: sortPicker
            anchors.right: parent.right
            width: 170 * GlassTheme.scale
            model: ["Phù hợp nhất", "Nhiều lượt tải", "Mới nhất"]
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
            text: contentBridge.searching ? "Đang tìm kiếm…" : contentBridge.totalHits.toLocaleString(Qt.locale("vi_VN"), 'f', 0) + " kết quả"
            color: GlassTheme.muted
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontNote
        }
        Button {
            anchors.right: parent.right
            visible: !root.instanceScoped
            height: 24
            label: "Bộ lọc nâng cao  ↗"
            quiet: true
            onClicked: advanced.open()
        }
    }
    InertialScroll {
        id: libraryViewport
        objectName: "libraryScroll"
        visible: !root.installedMode
        anchors.top: status.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        contentHeight: catalog.height + 20
        Column {
            id: catalog
            width: parent.width - 8
            spacing: 24
            Grid {
                id: grid
                width: parent.width
                columns: root.compactScope ? 1 : Math.max(1, Math.floor((width + 16) / (300 * GlassTheme.scale)))
                spacing: 16
                Repeater {
                    model: contentBridge.resultsModel
                    Rectangle {
                        id: tile
                        objectName: "projectCard-" + model.projectId
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: model.title + ", xem giới thiệu và phiên bản"
                        Accessible.onPressAction: projectBridge.openProject(model.projectId)
                        Keys.onReturnPressed: projectBridge.openProject(model.projectId)
                        Keys.onEnterPressed: projectBridge.openProject(model.projectId)
                        width: (grid.width - (grid.columns - 1) * 16) / grid.columns
                        height: (root.compactScope ? 126 : 218) * GlassTheme.scale
                        radius: 18
                        color: hover.hovered ? GlassTheme.raised : GlassTheme.cardSurface
                        Behavior on color {
                            ColorAnimation {
                                duration: GlassTheme.quick
                            }
                        }
                        CardMica {
                            objectName: "projectArtwork-" + model.projectId
                            source: model.iconUrl
                            radius: tile.radius
                            renderEnabled: tile.visible && root.visible && tile.y + tile.height >= libraryViewport.contentY && tile.y <= libraryViewport.contentY + libraryViewport.height
                        }
                        Rectangle {
                            anchors.fill: parent
                            radius: tile.radius
                            color: "transparent"
                            border.color: hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.50) : GlassTheme.stroke
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: function (mouse) {
                                if (mouse.x >= downloadButton.x && mouse.x <= downloadButton.x + downloadButton.width && mouse.y >= downloadButton.y && mouse.y <= downloadButton.y + downloadButton.height)
                                    return;
                                tile.forceActiveFocus();
                                projectBridge.openProject(model.projectId);
                            }
                        }
                        Legacy.ProjectIcon {
                            id: projectIcon
                            x: 20 * GlassTheme.scale
                            y: 20 * GlassTheme.scale
                            width: 52 * GlassTheme.scale
                            height: width
                            source: model.iconUrl
                            fallbackText: model.title
                        }
                        Column {
                            x: (root.compactScope ? 90 : 20) * GlassTheme.scale
                            y: (root.compactScope ? 16 : 90) * GlassTheme.scale
                            width: parent.width - x - 20 * GlassTheme.scale
                            spacing: 8 * GlassTheme.scale
                            Text {
                                width: parent.width
                                text: model.title
                                color: GlassTheme.text
                                font.family: GlassTheme.font
                                font.pixelSize: GlassTheme.fontSubheading
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                width: parent.width
                                text: model.description
                                objectName: "projectDescription-" + model.projectId
                                color: Legacy.Theme.mix(GlassTheme.muted, GlassTheme.text, 0.15)
                                font.family: GlassTheme.font
                                font.pixelSize: GlassTheme.fontLabel
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                lineHeight: 1.3
                            }
                        }
                        Text {
                            objectName: "projectMeta-" + model.projectId
                            width: Math.max(0, downloadButton.x - (root.compactScope ? 100 : 30) * GlassTheme.scale)
                            elide: Text.ElideRight
                            anchors.left: parent.left
                            anchors.leftMargin: (root.compactScope ? 90 : 20) * GlassTheme.scale
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 25 * GlassTheme.scale
                            text: Legacy.Theme.compact(model.downloads) + " tải  ·  " + (model.loaders.length ? model.loaders[0] : "Minecraft")
                            color: Legacy.Theme.mix(GlassTheme.muted, GlassTheme.text, 0.15)
                            font.family: GlassTheme.font
                            font.pixelSize: GlassTheme.fontNote
                        }
                        Button {
                            id: downloadButton
                            objectName: "projectDownload-" + model.projectId
                            anchors.right: parent.right
                            anchors.rightMargin: 14 * GlassTheme.scale
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 16 * GlassTheme.scale
                            label: model.installing ? "Đang cài…" : model.contentKind === "modpack" ? "Tạo bản chơi" : model.installed ? "Đã cài" : "Cài đặt"
                            height: 34 * GlassTheme.scale
                            clickable: !model.installing && !model.installed && !contentBridge.busy && !bridge.gameRunning && !bridge.storageBusy && !bridge.busy && (model.contentKind === "modpack" || (!!contentBridge.instanceId && !(root.kind === "mod" && contentBridge.loaderKind === "vanilla")))
                            onClicked: model.contentKind === "modpack" ? pack.openFor(model.projectId, model.title) : contentBridge.install(model.projectId)
                        }
                        HoverHandler {
                            id: hover
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }
            }
            Text {
                visible: !contentBridge.searching && !contentBridge.results.length
                text: "Chưa có kết quả. Thử đổi từ khóa hoặc nguồn nội dung."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: GlassTheme.fontControl
            }
            Button {
                visible: contentBridge.hasMore
                anchors.horizontalCenter: parent.horizontalCenter
                label: contentBridge.searching ? "Đang tải…" : "Xem thêm"
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
