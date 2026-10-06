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
    property var kindLabels: ({ "mod": "Mod", "shader": "Shader", "resourcepack": Tr.phrase("Gói tài nguyên"), "modpack": "Modpack" })

    readonly property string kind: kinds[kindTabs.currentIndex] || kinds[0]
    readonly property var sortKeys: ["relevance", "downloads", "follows", "newest", "updated"]
    readonly property var sortLabels: [Tr.phrase("Liên quan"), Tr.phrase("Nhiều tải"), Tr.phrase("Theo dõi"), Tr.phrase("Mới nhất"), Tr.phrase("Vừa cập nhật")]
    readonly property bool hasInstance: contentBridge.instanceId.length > 0
    readonly property bool modsBlocked: kind === "mod" && contentBridge.loaderKind === "vanilla"
    property bool gridMode: true
    signal navigate(int pageIndex)

    function runSearch() {
        contentBridge.search(page.kind, searchField.text, page.sortKeys[filters.sortIndex]);
    }
    // Mod đã có trong bản chơi: nút xám nhưng vẫn bấm được — hỏi lại rồi mới cài đè, đúng như
    // người chơi mong ("tôi biết nó có rồi, tôi muốn cài lại").
    property string pendingProjectId: ""
    function requestInstall(projectId, title, alreadyInstalled) {
        if (!alreadyInstalled) { contentBridge.install(projectId); return; }
        page.pendingProjectId = projectId;
        confirmDialog.acceptLabel = Tr.phrase("Cài thêm");
        confirmDialog.ask(Tr.phrase("Cài thêm ") + title + "?",
                          Tr.phrase("Bạn chắc chắn muốn cài thêm ") + page.kindLabels[page.kind].toLowerCase()
                          + Tr.phrase(" này chứ? ") + page.kindLabels[page.kind] + Tr.phrase(" đã tồn tại trong bản chơi — cài lại sẽ ghi đè file hiện có."),
                          function () { contentBridge.install(projectId); });
    }
    function refresh() {
        // Bridge phải biết loại TRƯỚC khi tìm: modpack thả bộ lọc thừa hưởng từ bản chơi đích,
        // nếu báo sau thì lần tìm này vẫn mang bộ lọc của loại cũ.
        contentBridge.setKind(page.kind);
        // Đọc danh sách đã cài của ĐÚNG loại đang xem trước (đọc đĩa, rẻ): cờ "Đã cài" trên
        // thẻ duyệt và tab Đã cài đều lấy từ đó, nên đổi chip là phải đọc lại.
        if (page.hasInstance && page.kind !== "modpack") contentBridge.refreshInstalled(page.kind);
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
        function onSourceChanged() { page.refresh(); }
        function onModpackInstalled(instanceId) { contentBridge.selectInstance(instanceId); }
        function onIdentified(found) { identifiedNote.text = found > 0 ? Tr.phrase("Nhận ra ") + found + " file." : Tr.phrase("Modrinth không biết file nào trong số này."); identifiedNote.visible = true; hideNote.restart(); }
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
        PageTitle {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter }
            caption: page.title
        }
        TabBar {
            id: modeTabs
            objectName: "modeTabs"
            anchors { left: parent.left; leftMargin: 170; verticalCenter: parent.verticalCenter }
            width: 230
            tabs: [Tr.phrase("Duyệt Modrinth"), Tr.phrase("Đã cài")]
            onCurrentIndexChanged: refreshSoon.restart()
        }
        Row {
            visible: page.kind !== "modpack"
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            spacing: 8
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: Tr.phrase("Cài vào"); color: Theme.textMuted; font.pixelSize: Theme.fontBody
            }
            Dropdown {
                width: 250
                placeholder: bridge.instances.length > 0 ? Tr.phrase("Chọn bản chơi") : Tr.phrase("Chưa có bản chơi")
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

            // ----- hàng 2: nguồn (trái) + loại nội dung (chip) -----
            Row {
                id: kindRow
                spacing: 8
                Repeater {
                    model: [{ key: "modrinth", label: "Modrinth" }, { key: "curseforge", label: "CurseForge" }]
                    Rectangle {
                        readonly property bool selected: modelData.key === contentBridge.source
                        width: sourceText.width + 26; height: 28; radius: Theme.modern ? 8 : 0
                        color: selected ? Theme.accentSoft : "transparent"
                        border.color: selected ? Theme.accent : Theme.border
                        Text {
                            id: sourceText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: Theme.fontBody; font.bold: parent.selected
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: contentBridge.setSource(modelData.key) }
                    }
                }
                Rectangle { width: 1; height: 28; color: Theme.border }
                Repeater {
                    model: page.kinds
                    Rectangle {
                        readonly property bool selected: index === kindTabs.currentIndex
                        width: kindText.width + 26; height: 28; radius: Theme.modern ? 8 : 0
                        color: selected ? Theme.accentSoft : "transparent"
                        border.color: selected ? Theme.accent : Theme.border
                        Text {
                            id: kindText
                            anchors.centerIn: parent
                            text: page.kindLabels[modelData]
                            color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: Theme.fontBody; font.bold: parent.selected
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
                        placeholder: Tr.phrase("Tìm ") + page.kindLabels[page.kind].toLowerCase() + "..."
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
                                width: 32; height: 32; radius: Theme.modern ? 8 : 0
                                color: selected ? Theme.accentSoft : Theme.surfaceHigh
                                Text { anchors.centerIn: parent; text: modelData; color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: Theme.fontHeading }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: page.gridMode = (index === 0) }
                            }
                        }
                    }
                }
                // Hàng lọc nằm NGANG dưới ô tìm: ba ô thu gọn thay cho cột dọc 210px cũ. Khay
                // của mỗi ô treo lên cửa sổ nên z ở đây chỉ cần cao hơn phần kết quả.
                FilterBar {
                    id: filters
                    z: 5
                    anchors { top: searchRow.bottom; topMargin: 10; left: parent.left; right: countLine.left
                              rightMargin: 12 }
                    loadersEnabled: page.kind === "mod"
                    versionsEnabled: true
                    sortKeys: page.sortKeys; sortLabels: page.sortLabels
                    onChanged: page.runSearch()
                }
                Text {
                    id: countLine
                    anchors { top: searchRow.bottom; topMargin: 18; right: parent.right }
                    text: contentBridge.searching ? Tr.phrase("Đang tìm...") : contentBridge.totalHits.toLocaleString(Qt.locale("vi_VN"), "f", 0) + Tr.phrase(" kết quả")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
                Rectangle {
                    id: shimmer
                    // Dải shimmer 2 px khi đang tìm, như bản mẫu.
                    anchors { top: filters.bottom; topMargin: 8; left: parent.left; right: parent.right }
                    height: 2; color: Theme.border; visible: contentBridge.searching
                    Rectangle {
                        width: parent.width * 0.3; height: 2; color: Theme.accent
                        SequentialAnimation on x {
                            running: contentBridge.searching; loops: Animation.Infinite
                            NumberAnimation { from: -width; to: parent.width; duration: 1400 }
                        }
                    }
                }

                Item {
                    id: results
                    anchors { top: filters.bottom; topMargin: 16; left: parent.left; right: parent.right; bottom: parent.bottom }

                    Text {
                        visible: !contentBridge.searching && contentBridge.results.length === 0
                        text: Tr.phrase("Không có kết quả.")
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody
                    }
                    Text {
                        anchors { top: parent.top; right: parent.right }
                        visible: page.modsBlocked && contentBridge.results.length > 0
                        text: Tr.phrase("Bản chơi đích không có mod loader — chọn bản Fabric/Forge/NeoForge để cài.")
                        color: Theme.accent; font.pixelSize: Theme.fontBody
                    }
                    GridView {
                        anchors.fill: parent
                        anchors.topMargin: page.modsBlocked ? 22 : 0
                        visible: page.gridMode
                        clip: true
                        // Bỏ cột lọc rồi nên phần này rộng gần gấp rưỡi: chia theo bề ngang
                        // thật (thẻ không dưới 330px) chứ đừng ghim cứng hai cột, không thì
                        // thẻ giãn ra thành hai dải dài ngoẵng.
                        cellWidth: Math.floor(width / Math.max(2, Math.floor(width / 330)))
                        cellHeight: 128
                        model: contentBridge.resultsModel
                        delegate: Item {
                            width: GridView.view.cellWidth; height: 128
                            ProjectCard {
                                anchors { fill: parent; rightMargin: 10; bottomMargin: 10 }
                                project: model
                                installable: page.hasInstance && !page.modsBlocked
                                onInstallRequested: function (projectId, title, alreadyInstalled) { page.requestInstall(projectId, title, alreadyInstalled); }
                                onModpackRequested: function (projectId, title) { modpackDialog.openFor(projectId, title); }
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
                            onInstallRequested: function (projectId, title, alreadyInstalled) { page.requestInstall(projectId, title, alreadyInstalled); }
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
                                label: contentBridge.searching ? Tr.phrase("Đang tải...") : Tr.phrase("Tải thêm")
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
                        placeholder: Tr.phrase("Tìm trong ") + page.kindLabels[page.kind].toLowerCase() + Tr.phrase(" đã cài...")
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
                                width: 32; height: 32; radius: Theme.modern ? 8 : 0
                                color: selected ? Theme.accentSoft : Theme.surfaceHigh
                                Text { anchors.centerIn: parent; text: modelData; color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: Theme.fontHeading }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: page.gridMode = (index === 0) }
                            }
                        }
                    }
                }
                Row {
                    id: installedActions
                    anchors { top: installedSearchRow.bottom; topMargin: 10; right: parent.right }
                    spacing: 8
                    ActionButton {
                        primary: false; height: 30
                        label: Tr.phrase("Kiểm tra bản mới")
                        clickable: page.hasInstance && !contentBridge.busy && contentBridge.installed.length > 0
                        onClicked: contentBridge.checkUpdates(page.kind)
                    }
                    ActionButton {
                        primary: false; height: 30
                        label: Tr.phrase("Nhận diện file chép tay")
                        clickable: page.hasInstance && !contentBridge.busy && contentBridge.installed.length > 0
                        onClicked: contentBridge.identifyInstalled(page.kind)
                    }
                }
                Text {
                    id: installedCount
                    anchors { top: installedSearchRow.bottom; topMargin: 16; left: parent.left }
                    text: contentBridge.installedShownCount + " / " + contentBridge.installed.length + " " + page.kindLabels[page.kind].toLowerCase()
                          + (page.hasInstance ? " trong " + contentBridge.instanceId : "")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
                Text {
                    id: identifiedNote
                    anchors { top: installedActions.bottom; topMargin: 6; right: parent.right }
                    visible: false
                    color: Theme.accent; font.pixelSize: Theme.fontBody
                    Timer { id: hideNote; interval: 5000; onTriggered: identifiedNote.visible = false }
                }
                Text {
                    anchors { top: installedCount.bottom; topMargin: 18; horizontalCenter: parent.horizontalCenter }
                    visible: contentBridge.installedShownCount === 0
                    text: !page.hasInstance ? Tr.phrase("Tạo một bản chơi trước.")
                        : contentBridge.installed.length === 0 ? Tr.phrase("Chưa cài gì. Sang tab Duyệt Modrinth để thêm.")
                        : Tr.phrase("Không có mục nào khớp.")
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
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
                            onUpdateRequested: function (fileName) { contentBridge.updateInstalled(page.kind, fileName); }
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
                        onUpdateRequested: function (fileName) { contentBridge.updateInstalled(page.kind, fileName); }
                    }
                }
            }
        }
    }

    ModpackDialog { id: modpackDialog; objectName: "modpackDialog"; anchors.fill: parent }
}
