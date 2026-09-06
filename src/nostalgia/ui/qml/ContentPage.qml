import QtQuick

/*
  Thư viện nội dung (mod, shader, gói tài nguyên) theo bản mẫu: hàng tab loại, ô tìm rộng kèm
  nút lưới/danh sách và số kết quả, cột lọc trái (loader, sắp xếp, phiên bản game), lưới thẻ
  hai cột. Duyệt được không cần bản chơi; bấm Cài thì cài vào bản chơi chọn ở góc trên phải.
  Tab "Đã cài" quản lý file trong thư mục bản chơi đó.
*/
Item {
    id: page
    objectName: "contentPage"
    property string title: ""
    property var kinds: ["mod"]
    property var kindLabels: ({ "mod": "Mod", "shader": "Shader", "resourcepack": "Gói tài nguyên" })
    readonly property string kind: kinds[kindTabs.currentIndex] || kinds[0]
    readonly property var sortKeys: ["relevance", "downloads", "follows", "newest", "updated"]
    readonly property var sortLabels: ["Liên quan", "Nhiều tải", "Theo dõi", "Mới nhất", "Vừa cập nhật"]
    readonly property bool hasInstance: contentBridge.instanceId.length > 0
    readonly property bool modsBlocked: kind === "mod" && contentBridge.loaderKind === "vanilla"
    property bool gridMode: true
    signal navigate(int pageIndex)

    function runSearch() { contentBridge.search(page.kind, searchField.text, page.sortKeys[filters.sortIndex]); }
    function refresh() {
        // Đọc danh sách đã cài của ĐÚNG loại đang xem trước (đọc đĩa, rẻ): cờ "Đã cài" trên
        // thẻ duyệt và tab Đã cài đều lấy từ đó, nên đổi chip là phải đọc lại.
        if (page.hasInstance) contentBridge.refreshInstalled(page.kind);
        if (modeTabs.currentIndex === 0) page.runSearch();
    }

    Component.onCompleted: {
        if (!contentBridge.instanceId && bridge.instances.length > 0)
            contentBridge.selectInstance(bridge.instances[0].instanceId);
        page.refresh();
    }
    Connections {
        target: contentBridge
        function onTargetChanged() { page.refresh(); }
    }
    Timer { id: debounce; interval: 300; onTriggered: page.runSearch() }
    // Timer chết cùng trang, khác Qt.callLater có thể bắn sau khi trang đã bị huỷ.
    Timer { id: refreshSoon; interval: 0; onTriggered: page.refresh() }

    // ----- hàng 1: tiêu đề + chế độ + bản chơi đích -----
    Item {
        id: header
        z: 10
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 50
        Text {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            text: page.title; color: Theme.text; font.pixelSize: 22; font.bold: true
        }
        TabBar {
            id: modeTabs
            objectName: "modeTabs"
            anchors { left: parent.left; leftMargin: 170; verticalCenter: parent.verticalCenter }
            width: 230
            tabs: ["Duyệt Modrinth", "Đã cài"]
            onCurrentIndexChanged: refreshSoon.restart()
        }
        Row {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            spacing: 8
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Cài vào"; color: Theme.textMuted; font.pixelSize: 11
            }
            Dropdown {
                width: 250
                placeholder: bridge.instances.length > 0 ? "Chọn bản chơi" : "Chưa có bản chơi"
                model: bridge.instances.map(function (instance) { return instance.label + "  (" + instance.versionId + ")"; })
                currentIndex: bridge.instances.findIndex(function (instance) { return instance.instanceId === contentBridge.instanceId; })
                onActivated: function (index) { contentBridge.selectInstance(bridge.instances[index].instanceId); }
            }
        }
    }

    Panel {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: 6 }

        Item {
            anchors.fill: parent

            // ----- hàng 2: loại nội dung (chip) -----
            Row {
                id: kindRow
                spacing: 8
                Repeater {
                    model: page.kinds
                    Rectangle {
                        readonly property bool selected: index === kindTabs.currentIndex
                        width: kindText.width + 26; height: 28; radius: 14
                        color: selected ? Theme.accentSoft : "transparent"
                        border.color: selected ? Theme.accent : Theme.border
                        Text {
                            id: kindText
                            anchors.centerIn: parent
                            text: page.kindLabels[modelData]
                            color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: 12; font.bold: parent.selected
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: kindTabs.currentIndex = index }
                    }
                }
            }
            // Hoãn một nhịp: `page.kind` là binding trên currentIndex; gọi refresh ngay trong handler
            // thì nó còn mang loại CŨ và chip Shader hiện kết quả của Gói tài nguyên (lỗi thật).
            Item { id: kindTabs; objectName: "kindTabs"; property int currentIndex: 0; onCurrentIndexChanged: refreshSoon.restart() }

            // ----- Duyệt -----
            Item {
                anchors { top: kindRow.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: modeTabs.currentIndex === 0

                Item {
                    id: searchRow
                    anchors { left: parent.left; right: parent.right }
                    height: 36
                    TextField {
                        id: searchField
                        anchors { left: parent.left; right: viewToggle.left; rightMargin: 10; verticalCenter: parent.verticalCenter }
                        height: 36
                        placeholder: "Tìm " + page.kindLabels[page.kind].toLowerCase() + "..."
                        onTextChanged: debounce.restart()
                        onAccepted: page.runSearch()
                    }
                    Row {
                        id: viewToggle
                        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                        spacing: 2
                        Repeater {
                            model: ["▦", "☰"]
                            Rectangle {
                                readonly property bool selected: (index === 0) === page.gridMode
                                width: 32; height: 32; radius: 6
                                color: selected ? Theme.accentSoft : Theme.surfaceHigh
                                Text { anchors.centerIn: parent; text: modelData; color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: 14 }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: page.gridMode = (index === 0) }
                            }
                        }
                    }
                }
                Text {
                    id: countLine
                    anchors { top: searchRow.bottom; topMargin: 8; horizontalCenter: parent.horizontalCenter }
                    text: contentBridge.searching ? "Đang tìm..." : contentBridge.totalHits.toLocaleString(Qt.locale("vi_VN"), "f", 0) + " kết quả"
                    color: Theme.textMuted; font.pixelSize: 12
                }
                Rectangle {
                    // Dải shimmer 2 px khi đang tìm, như bản mẫu.
                    anchors { top: countLine.bottom; topMargin: 6; left: parent.left; right: parent.right }
                    height: 2; color: Theme.border; visible: contentBridge.searching
                    Rectangle {
                        width: parent.width * 0.3; height: 2; color: Theme.accent
                        SequentialAnimation on x {
                            running: contentBridge.searching; loops: Animation.Infinite
                            NumberAnimation { from: -width; to: parent.width; duration: 1400 }
                        }
                    }
                }

                FilterSidebar {
                    id: filters
                    anchors { top: countLine.bottom; topMargin: 16; left: parent.left; bottom: parent.bottom }
                    width: 210
                    loadersEnabled: page.kind === "mod"
                    sortKeys: page.sortKeys; sortLabels: page.sortLabels
                    onChanged: page.runSearch()
                }
                Rectangle { anchors { top: filters.top; bottom: filters.bottom; left: filters.right; leftMargin: 10 } width: 1; color: Theme.border }

                Item {
                    id: results
                    anchors { top: countLine.bottom; topMargin: 16; left: filters.right; leftMargin: 24; right: parent.right; bottom: parent.bottom }

                    Text {
                        visible: !contentBridge.searching && contentBridge.results.length === 0
                        text: "Không có kết quả."
                        color: Theme.textMuted; font.pixelSize: 12
                    }
                    Text {
                        anchors { top: parent.top; right: parent.right }
                        visible: page.modsBlocked && contentBridge.results.length > 0
                        text: "Bản chơi đích không có mod loader — chọn bản Fabric/Forge/NeoForge để cài."
                        color: Theme.accent; font.pixelSize: 11
                    }
                    GridView {
                        anchors.fill: parent
                        anchors.topMargin: page.modsBlocked ? 22 : 0
                        visible: page.gridMode
                        clip: true
                        cellWidth: Math.floor(width / 2); cellHeight: 128
                        model: contentBridge.resultsModel
                        delegate: Item {
                            width: GridView.view.cellWidth; height: 128
                            ProjectCard {
                                anchors { fill: parent; rightMargin: 10; bottomMargin: 10 }
                                project: model
                                installable: page.hasInstance && !page.modsBlocked
                                onInstallRequested: function (projectId) { contentBridge.install(projectId); }
                            }
                        }
                        footer: loadMore
                    }
                    ListView {
                        anchors.fill: parent
                        anchors.topMargin: page.modsBlocked ? 22 : 0
                        visible: !page.gridMode
                        clip: true; spacing: 8
                        model: contentBridge.resultsModel
                        delegate: ProjectRow {
                            width: ListView.view.width
                            project: model
                            installable: page.hasInstance && !page.modsBlocked
                            onInstallRequested: function (projectId) { contentBridge.install(projectId); }
                        }
                        footer: loadMore
                    }
                    Component {
                        id: loadMore
                        Item {
                            width: results.width
                            height: contentBridge.hasMore ? 52 : 0
                            ActionButton {
                                anchors.centerIn: parent
                                visible: contentBridge.hasMore
                                primary: false
                                label: contentBridge.searching ? "Đang tải..." : "Tải thêm"
                                clickable: !contentBridge.searching
                                onClicked: contentBridge.loadMore()
                            }
                        }
                    }
                }
            }

            // ----- Đã cài: cùng bố cục thư viện — ô tìm, số mục, lưới/danh sách -----
            Item {
                anchors { top: kindRow.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: modeTabs.currentIndex === 1

                Item {
                    id: installedSearchRow
                    anchors { left: parent.left; right: parent.right }
                    height: 36
                    TextField {
                        anchors { left: parent.left; right: installedToggle.left; rightMargin: 10; verticalCenter: parent.verticalCenter }
                        height: 36
                        placeholder: "Tìm trong " + page.kindLabels[page.kind].toLowerCase() + " đã cài..."
                        onTextChanged: contentBridge.setInstalledFilter(text)
                    }
                    Row {
                        id: installedToggle
                        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                        spacing: 2
                        Repeater {
                            model: ["▦", "☰"]
                            Rectangle {
                                readonly property bool selected: (index === 0) === page.gridMode
                                width: 32; height: 32; radius: 6
                                color: selected ? Theme.accentSoft : Theme.surfaceHigh
                                Text { anchors.centerIn: parent; text: modelData; color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: 14 }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: page.gridMode = (index === 0) }
                            }
                        }
                    }
                }
                Text {
                    id: installedCount
                    anchors { top: installedSearchRow.bottom; topMargin: 8; horizontalCenter: parent.horizontalCenter }
                    text: contentBridge.installedShownCount + " / " + contentBridge.installed.length + " " + page.kindLabels[page.kind].toLowerCase()
                          + (page.hasInstance ? " trong " + contentBridge.instanceId : "")
                    color: Theme.textMuted; font.pixelSize: 12
                }
                Text {
                    anchors { top: installedCount.bottom; topMargin: 18; horizontalCenter: parent.horizontalCenter }
                    visible: contentBridge.installedShownCount === 0
                    text: !page.hasInstance ? "Tạo một bản chơi trước."
                        : contentBridge.installed.length === 0 ? "Chưa cài gì. Sang tab Duyệt Modrinth để thêm."
                        : "Không có mục nào khớp."
                    color: Theme.textMuted; font.pixelSize: 12
                }
                GridView {
                    id: installedGrid
                    anchors { top: installedCount.bottom; topMargin: 16; left: parent.left; right: parent.right; bottom: parent.bottom }
                    visible: page.gridMode
                    clip: true
                    cellWidth: Math.floor(width / 2); cellHeight: 128
                    model: contentBridge.installedModel
                    delegate: Item {
                        width: installedGrid.cellWidth; height: 128
                        InstalledCard {
                            anchors { fill: parent; rightMargin: 10; bottomMargin: 10 }
                            installedContent: model
                            toggleable: page.kind === "mod"
                            onToggled: function (fileName, enabled) { contentBridge.setEnabled(page.kind, fileName, enabled); }
                            onRemoveRequested: function (fileName) { contentBridge.remove(page.kind, fileName); }
                        }
                    }
                }
                ListView {
                    id: installedList
                    anchors { top: installedCount.bottom; topMargin: 16; left: parent.left; right: parent.right; bottom: parent.bottom }
                    visible: !page.gridMode
                    clip: true; spacing: 6
                    model: contentBridge.installedModel
                    delegate: InstalledRow {
                        width: installedList.width
                        installedContent: model
                        toggleable: page.kind === "mod"
                        onToggled: function (fileName, enabled) { contentBridge.setEnabled(page.kind, fileName, enabled); }
                        onRemoveRequested: function (fileName) { contentBridge.remove(page.kind, fileName); }
                    }
                }
            }
        }
    }
}
