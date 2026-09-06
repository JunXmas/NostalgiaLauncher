import QtQuick

/*
  Cột lọc bên trái của thư viện mod: LOADERS (chọn nhiều), SORT (chọn một), GAME VERSION
  (ô tìm + danh sách chọn nhiều, lấy từ danh mục Mojang). Trạng thái lọc sống ở contentBridge
  để đổi trang quay lại vẫn còn.
*/
Item {
    id: root
    property bool loadersEnabled: true
    property var sortKeys: []
    property var sortLabels: []
    property int sortIndex: 0
    signal changed()

    readonly property var loaderNames: ["fabric", "forge", "neoforge", "quilt"]
    readonly property var loaderLabels: ["Fabric", "Forge", "NeoForge", "Quilt"]
    property string versionFilter: ""

    Component.onCompleted: if (catalogBridge.releasedVersions.length === 0) catalogBridge.loadReleasedVersions()

    Flickable {
        anchors.fill: parent
        contentHeight: column.height
        clip: true

        Column {
            id: column
            width: parent.width
            spacing: 18

            Row {
                width: parent.width
                spacing: 14
                Column {
                    width: (parent.width - 14) / 2
                    spacing: 4
                    opacity: root.loadersEnabled ? 1 : 0.4
                    Text { text: "LOADERS"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.4; font.bold: true }
                    Item { width: 1; height: 4 }
                    Repeater {
                        model: root.loaderNames
                        CheckRow {
                            label: root.loaderLabels[index]
                            enabled: root.loadersEnabled
                            checked: contentBridge.selectedLoaders.indexOf(modelData) >= 0
                            onToggled: function (checked) { contentBridge.setLoaderSelected(modelData, checked); root.changed(); }
                        }
                    }
                }
                Rectangle { width: 1; height: 150; color: Theme.border }
                Column {
                    width: (parent.width - 14) / 2 - 15
                    spacing: 2
                    Text { text: "SORT"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.4; font.bold: true }
                    Item { width: 1; height: 4 }
                    Repeater {
                        model: root.sortLabels
                        Rectangle {
                            readonly property bool selected: index === root.sortIndex
                            width: parent.width; height: 26; radius: 6
                            color: selected ? Theme.accentSoft : "transparent"
                            Text {
                                anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                                text: modelData
                                color: parent.selected ? Theme.accent : Theme.textMuted; font.pixelSize: 12
                            }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: { root.sortIndex = index; root.changed(); } }
                        }
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: Theme.border }

            Column {
                width: parent.width
                spacing: 8
                Row {
                    width: parent.width
                    Text { text: "GAME VERSION"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.4; font.bold: true
                           anchors.verticalCenter: parent.verticalCenter }
                    Item { width: parent.width - 150; height: 1 }
                    Rectangle {
                        visible: contentBridge.selectedGameVersions.length > 0
                        width: countText.width + 22; height: 20; radius: 10
                        color: Theme.accentSoft; border.color: Theme.accent
                        Row {
                            id: countText
                            anchors.centerIn: parent; spacing: 5
                            Text { text: contentBridge.selectedGameVersions.length; color: Theme.accent; font.pixelSize: 10; font.bold: true }
                            Text { text: "✕"; color: Theme.accent; font.pixelSize: 10 }
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: { contentBridge.clearGameVersions(); root.changed(); } }
                    }
                }
                TextField {
                    width: parent.width; height: 30
                    placeholder: "Tìm phiên bản..."
                    onTextChanged: root.versionFilter = text
                }
                Column {
                    width: parent.width
                    spacing: 2
                    Repeater {
                        model: catalogBridge.releasedVersions.filter(function (released) {
                            return !root.versionFilter || released.versionId.indexOf(root.versionFilter) >= 0;
                        }).slice(0, 60)
                        CheckRow {
                            label: modelData.versionId
                            checked: contentBridge.selectedGameVersions.indexOf(modelData.versionId) >= 0
                            onToggled: function (checked) { contentBridge.setGameVersionSelected(modelData.versionId, checked); root.changed(); }
                        }
                    }
                }
                Text {
                    visible: catalogBridge.releasedVersions.length === 0
                    text: catalogBridge.busy ? "Đang tải danh mục..." : "Không tải được danh mục phiên bản."
                    color: Theme.textMuted; font.pixelSize: 11
                }
            }
        }
    }
}
