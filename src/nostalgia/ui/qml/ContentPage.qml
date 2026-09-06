import QtQuick

/*
  Trang nội dung dùng chung cho MOD và TÀI NGUYÊN. `kinds` là các loại trang này quản lý
  (mod; hoặc resourcepack + shader). Hai tab: Duyệt Modrinth và Đã cài. Mọi thứ lọc theo bản
  chơi đang chọn — không có đường "cài rồi tính".
*/
Item {
    id: page
    objectName: "contentPage"
    property alias mode: modeTabs.currentIndex
    property string title: ""
    property var kinds: ["mod"]
    property var kindLabels: ({ "mod": "Mod", "resourcepack": "Gói tài nguyên", "shader": "Shader" })
    readonly property string kind: kinds[kindTabs.currentIndex] || kinds[0]
    readonly property var sortKeys: ["relevance", "downloads", "follows", "newest", "updated"]
    readonly property var sortLabels: ["Liên quan", "Nhiều tải", "Theo dõi", "Mới nhất", "Vừa cập nhật"]
    readonly property bool hasInstance: contentBridge.instanceId.length > 0
    readonly property bool modsBlocked: kind === "mod" && contentBridge.loaderKind === "vanilla"
    signal navigate(int pageIndex)

    function runSearch() {
        if (!page.hasInstance) return;
        contentBridge.search(page.kind, searchField.text, page.sortKeys[sortBox.currentIndex]);
    }
    function refresh() {
        if (!page.hasInstance) return;
        if (modeTabs.currentIndex === 0) page.runSearch();
        else contentBridge.refreshInstalled(page.kind);
    }

    Component.onCompleted: {
        // Chưa chọn bản chơi nào thì lấy bản đầu tiên: người dùng ít khi muốn một trang trống.
        if (!contentBridge.instanceId && bridge.instances.length > 0)
            contentBridge.selectInstance(bridge.instances[0].instanceId);
        page.refresh();
    }
    Connections {
        target: contentBridge
        function onTargetChanged() { page.refresh(); }
        function onInstallFinished(title) { if (modeTabs.currentIndex === 1) contentBridge.refreshInstalled(page.kind); }
    }
    Timer { id: debounce; interval: 300; onTriggered: page.runSearch() }

    // ----- hàng đầu: tiêu đề + chọn bản chơi -----
    Item {
        id: header
        z: 10
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Theme.gap }
        height: 66
        Column {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            spacing: 3
            Text { text: page.title; color: Theme.text; font.pixelSize: 24; font.bold: true }
            Text {
                text: page.hasInstance
                      ? "Minecraft " + contentBridge.gameVersion + "  ·  " + (contentBridge.loaderKind === "vanilla" ? "không loader" : contentBridge.loaderKind)
                      : "Chưa có bản chơi nào."
                color: Theme.textMuted; font.pixelSize: 12
            }
        }
        Dropdown {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            width: 260
            placeholder: "Chọn bản chơi"
            model: bridge.instances.map(function (instance) { return instance.label + "  (" + instance.versionId + ")"; })
            currentIndex: bridge.instances.findIndex(function (instance) { return instance.instanceId === contentBridge.instanceId; })
            onActivated: function (index) { contentBridge.selectInstance(bridge.instances[index].instanceId); }
        }
    }

    Panel {
        anchors { top: header.bottom; left: parent.left; right: parent.right; bottom: parent.bottom
                  margins: Theme.gap; topMargin: 0 }

        Item {
            anchors.fill: parent

            Row {
                id: tabRow
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 36
                spacing: 28
                TabBar { id: modeTabs; tabs: ["Duyệt Modrinth", "Đã cài"]; width: 220
                         onCurrentIndexChanged: page.refresh() }
                TabBar {
                    id: kindTabs
                    visible: page.kinds.length > 1
                    tabs: page.kinds.map(function (k) { return page.kindLabels[k]; })
                    width: 260
                    onCurrentIndexChanged: page.refresh()
                }
            }

            // ----- Duyệt -----
            Item {
                anchors { top: tabRow.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: modeTabs.currentIndex === 0

                Row {
                    id: filters
                    spacing: 10
                    TextField {
                        id: searchField
                        width: 360
                        placeholder: "Tìm " + page.kindLabels[page.kind].toLowerCase() + "..."
                        onTextChanged: debounce.restart()
                        onAccepted: page.runSearch()
                    }
                    Dropdown {
                        id: sortBox
                        width: 160
                        model: page.sortLabels
                        currentIndex: 0
                        onActivated: page.runSearch()
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: contentBridge.searching ? "Đang tìm..." : (contentBridge.totalHits + " kết quả")
                        color: Theme.textMuted; font.pixelSize: 12
                        visible: page.hasInstance
                    }
                }

                Text {
                    anchors { top: filters.bottom; topMargin: 24; left: parent.left }
                    visible: !page.hasInstance || page.modsBlocked
                             || (!contentBridge.searching && contentBridge.results.length === 0)
                    text: !page.hasInstance ? "Tạo một bản chơi trước, ở trang BẢN CHƠI."
                        : page.modsBlocked ? "Bản chơi này không có mod loader. Tạo bản chơi Fabric để cài mod."
                        : "Không có kết quả."
                    color: Theme.textMuted; font.pixelSize: 12
                }

                ListView {
                    id: resultList
                    anchors { top: filters.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                    clip: true
                    spacing: 8
                    model: page.modsBlocked ? [] : contentBridge.results
                    delegate: ProjectRow {
                        width: resultList.width
                        project: modelData
                        installable: !page.modsBlocked
                        onInstallRequested: function (projectId) { contentBridge.install(projectId); }
                    }
                    footer: Item {
                        width: resultList.width
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

            // ----- Đã cài -----
            Item {
                anchors { top: tabRow.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: modeTabs.currentIndex === 1

                Text {
                    id: installedCount
                    text: contentBridge.installed.length + " " + page.kindLabels[page.kind].toLowerCase()
                          + (page.hasInstance ? " trong " + contentBridge.instanceId : "")
                    color: Theme.textMuted; font.pixelSize: 12
                }
                Text {
                    anchors { top: installedCount.bottom; topMargin: 18 }
                    visible: contentBridge.installed.length === 0
                    text: page.hasInstance ? "Chưa cài gì. Sang tab Duyệt Modrinth để thêm." : "Tạo một bản chơi trước."
                    color: Theme.textMuted; font.pixelSize: 12
                }
                ListView {
                    id: installedList
                    anchors { top: installedCount.bottom; topMargin: 12; left: parent.left; right: parent.right; bottom: parent.bottom }
                    clip: true
                    spacing: 6
                    model: contentBridge.installed
                    delegate: InstalledRow {
                        width: installedList.width
                        installedContent: modelData
                        toggleable: page.kind === "mod"
                        onToggled: function (fileName, enabled) { contentBridge.setEnabled(page.kind, fileName, enabled); }
                        onRemoveRequested: function (fileName) { contentBridge.remove(page.kind, fileName); }
                    }
                }
            }
        }
    }
}
