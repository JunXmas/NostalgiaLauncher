import QtQuick
import "../" as Legacy

Item {
    id: root
    objectName: "minimalLibrary"
    property string kind: "modpack"
    property string sort: "relevance"
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
    ]
    function refresh() {
        contentBridge.setKind(root.kind);
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
        height: 86
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Text {
                text: "Khám phá"
                color: GlassTheme.text
                font.family: GlassTheme.font
                font.pixelSize: 30
                font.weight: Font.DemiBold
            }
            Text {
                text: "Một thế giới quen thuộc. Những cách chơi mới."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: 13
            }
        }
        Select {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 145
            model: ["Modrinth", "CurseForge"]
            currentIndex: contentBridge.source === "curseforge" ? 1 : 0
            onActivated: function (index) {
                contentBridge.setSource(index ? "curseforge" : "modrinth");
                root.refresh();
            }
        }
    }
    Row {
        id: types
        anchors.top: header.bottom
        anchors.topMargin: 8
        spacing: 8
        Repeater {
            model: root.kinds
            Button {
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
            label: "Đã cài  ↗"
            quiet: true
            onClicked: root.advancedRequested()
        }
    }
    Item {
        id: filters
        anchors.top: types.bottom
        anchors.topMargin: 24
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
            width: 170
            model: ["Phù hợp nhất", "Nhiều lượt tải", "Mới nhất"]
            onActivated: function (index) {
                root.sort = ["relevance", "downloads", "newest"][index];
                root.refresh();
            }
        }
    }
    Item {
        id: status
        anchors.top: filters.bottom
        anchors.topMargin: 18
        width: parent.width
        height: 26
        Text {
            text: contentBridge.searching ? "Đang tìm kiếm…" : contentBridge.totalHits.toLocaleString(Qt.locale("vi_VN"), 'f', 0) + " kết quả"
            color: GlassTheme.muted
            font.family: GlassTheme.font
            font.pixelSize: 11
        }
        Button {
            anchors.right: parent.right
            height: 24
            label: "Bộ lọc nâng cao  ↗"
            quiet: true
            onClicked: root.advancedRequested()
        }
    }
    InertialScroll {
        objectName: "libraryScroll"
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
                columns: Math.max(1, Math.floor((width + 16) / 300))
                spacing: 16
                Repeater {
                    model: contentBridge.resultsModel
                    Rectangle {
                        id: tile
                        width: (grid.width - (grid.columns - 1) * 16) / grid.columns
                        height: 218
                        radius: 18
                        color: hover.hovered ? GlassTheme.raised : GlassTheme.cardSurface
                        Behavior on color {
                            ColorAnimation {
                                duration: GlassTheme.quick
                            }
                        }
                        CardMica {
                            source: model.iconUrl
                            radius: tile.radius
                        }
                        Rectangle {
                            anchors.fill: parent
                            radius: tile.radius
                            color: "transparent"
                            border.color: hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.50) : GlassTheme.stroke
                        }
                        Legacy.ProjectIcon {
                            id: projectIcon
                            x: 20
                            y: 20
                            width: 52
                            height: 52
                            source: model.iconUrl
                            fallbackText: model.title
                        }
                        Column {
                            x: 20
                            y: 90
                            width: parent.width - 40
                            spacing: 8
                            Text {
                                width: parent.width
                                text: model.title
                                color: GlassTheme.text
                                font.family: GlassTheme.font
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                width: parent.width
                                text: model.description
                                color: Legacy.Theme.mix(GlassTheme.muted, GlassTheme.text, 0.15)
                                font.family: GlassTheme.font
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                lineHeight: 1.3
                            }
                        }
                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 20
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 25
                            text: Legacy.Theme.compact(model.downloads) + " tải  ·  " + (model.loaders.length ? model.loaders[0] : "Minecraft")
                            color: Legacy.Theme.mix(GlassTheme.muted, GlassTheme.text, 0.15)
                            font.family: GlassTheme.font
                            font.pixelSize: 11
                        }
                        Button {
                            anchors.right: parent.right
                            anchors.rightMargin: 14
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 16
                            label: model.installing ? "Đang cài…" : model.contentKind === "modpack" ? "Tạo bản chơi" : model.installed ? "Đã cài" : "Cài đặt"
                            height: 34
                            clickable: !model.installing && !model.installed && !contentBridge.busy && (model.contentKind === "modpack" || (!!contentBridge.instanceId && !(root.kind === "mod" && contentBridge.loaderKind === "vanilla")))
                            onClicked: model.contentKind === "modpack" ? pack.openFor(model.projectId, model.title) : contentBridge.install(model.projectId)
                        }
                        HoverHandler {
                            id: hover
                        }
                    }
                }
            }
            Text {
                visible: !contentBridge.searching && !contentBridge.results.length
                text: "Chưa có kết quả. Thử đổi từ khóa hoặc nguồn nội dung."
                color: GlassTheme.muted
                font.family: GlassTheme.font
                font.pixelSize: 14
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
    Legacy.ModpackDialog {
        id: pack
        anchors.fill: parent
    }
}
