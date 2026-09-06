import QtQuick

/*
  Hộp thoại tạo bản chơi, hai cột như bản mẫu: trái là form (tên, loader, RAM, nút tạo),
  phải là danh sách chọn — bước 1 phiên bản game, bước 2 (chỉ Fabric) phiên bản loader.

  Forge và NeoForge hiện ở dạng mờ: lõi chưa cài được chúng, và một nút bấm được mà không
  làm gì thì tệ hơn một nút nói thẳng là chưa có.
*/
Item {
    id: dialog
    visible: false
    z: 100

    property string loaderKind: "vanilla"
    property string gameVersion: ""
    property string loaderVersion: ""
    property string majorFilter: ""
    readonly property var loaderChoices: [
        { key: "vanilla",  label: "Vanilla",  ready: true },
        { key: "fabric",   label: "Fabric",   ready: true },
        { key: "forge",    label: "Forge",    ready: false },
        { key: "neoforge", label: "NeoForge", ready: false }
    ]
    readonly property bool needsLoaderStep: loaderKind === "fabric"
    readonly property bool canCreate: gameVersion.length > 0 && nameField.text.trim().length > 0
                                      && (!needsLoaderStep || loaderVersion.length > 0) && !bridge.busy
    readonly property var majors: {
        var seen = [];
        for (var i = 0; i < catalogBridge.releasedVersions.length; i++) {
            var major = catalogBridge.releasedVersions[i].major;
            if (seen.indexOf(major) < 0) seen.push(major);
        }
        return seen;
    }
    readonly property var shownVersions: catalogBridge.releasedVersions.filter(function (released) {
        return !dialog.majorFilter || released.major === dialog.majorFilter;
    })

    function openDialog() {
        dialog.gameVersion = ""; dialog.loaderVersion = ""; dialog.majorFilter = "";
        nameField.text = ""; heapField.text = "";
        dialog.visible = true;
        if (catalogBridge.releasedVersions.length === 0) catalogBridge.loadReleasedVersions();
    }
    function pickGameVersion(versionId) {
        dialog.gameVersion = versionId;
        dialog.loaderVersion = "";
        if (dialog.needsLoaderStep) catalogBridge.loadFabricLoaders(versionId);
    }

    Connections {
        target: catalogBridge
        function onCreated(instanceId) { dialog.visible = false; }
    }

    // Màn tối phía sau; bấm ra ngoài là đóng.
    Rectangle {
        anchors.fill: parent
        color: "#b3000000"
        TapHandler { onTapped: if (!bridge.busy) dialog.visible = false }
    }

    Rectangle {
        id: box
        anchors.centerIn: parent
        width: Math.min(parent.width - 60, 980)
        height: Math.min(parent.height - 60, 640)
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        scale: dialog.visible ? 1 : 0.96
        Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        TapHandler { }  // nuốt bấm để không đóng hộp

        // ----- cột trái: form -----
        Column {
            id: form
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 26 }
            width: 330
            spacing: 18

            Column {
                spacing: 4
                Text { text: "Tạo bản chơi"; color: Theme.text; font.pixelSize: 20; font.bold: true }
                Text {
                    text: dialog.loaderChoices.find(function (c) { return c.key === dialog.loaderKind; }).label
                          + (dialog.gameVersion ? "  ·  " + dialog.gameVersion : "")
                          + (dialog.loaderVersion ? "  ·  loader " + dialog.loaderVersion : "")
                    color: Theme.accent; font.pixelSize: 12
                }
            }

            Column {
                spacing: 6; width: parent.width
                Text { text: "TÊN"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                TextField { id: nameField; width: parent.width; placeholder: "vd. Sinh tồn vui" }
            }

            Column {
                spacing: 6; width: parent.width
                Text { text: "LOADER"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                Row {
                    spacing: 8
                    Repeater {
                        model: dialog.loaderChoices
                        Rectangle {
                            readonly property bool selected: modelData.key === dialog.loaderKind
                            width: 76; height: 56; radius: Theme.radiusSmall
                            color: selected ? Theme.accentSoft : Theme.surfaceHigh
                            border.color: selected ? Theme.accent : Theme.border
                            border.width: 1
                            opacity: modelData.ready ? 1 : 0.45
                            Column {
                                anchors.centerIn: parent; spacing: 2
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: modelData.label; color: selected ? Theme.accent : Theme.text
                                    font.pixelSize: 11; font.bold: true
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    visible: !modelData.ready
                                    text: "chưa hỗ trợ"; color: Theme.textMuted; font.pixelSize: 9
                                }
                            }
                            HoverHandler { cursorShape: modelData.ready ? Qt.PointingHandCursor : Qt.ArrowCursor }
                            TapHandler {
                                enabled: modelData.ready
                                onTapped: {
                                    dialog.loaderKind = modelData.key;
                                    dialog.loaderVersion = "";
                                    if (dialog.needsLoaderStep && dialog.gameVersion) catalogBridge.loadFabricLoaders(dialog.gameVersion);
                                }
                            }
                        }
                    }
                }
            }

            Column {
                spacing: 6; width: parent.width
                Text { text: "RAM (MB, để trống = mặc định)"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                TextField { id: heapField; width: 140; placeholder: "vd. 4096" }
            }

            Item { width: 1; height: form.height - 420 }

            ActionButton {
                width: parent.width
                height: 44
                label: bridge.busy ? "Đang cài..." : "Tạo bản chơi"
                clickable: dialog.canCreate
                onClicked: catalogBridge.createInstance(nameField.text, dialog.gameVersion, dialog.loaderKind,
                                                  dialog.loaderVersion, parseInt(heapField.text) || 0)
            }
            Text {
                visible: bridge.busy
                width: parent.width
                text: bridge.progressText
                color: Theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight
            }
        }

        Rectangle { x: form.x + form.width + 22; y: 26; width: 1; height: box.height - 52; color: Theme.border }

        // ----- cột phải: chọn phiên bản -----
        Item {
            anchors { left: form.right; leftMargin: 44; right: parent.right; top: parent.top; bottom: parent.bottom; margins: 26 }

            Row {
                id: pickHeader
                anchors { left: parent.left; right: parent.right }
                height: 34
                spacing: 12
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: dialog.needsLoaderStep && dialog.gameVersion
                          ? "② Chọn phiên bản Fabric loader" : "① Chọn phiên bản Minecraft"
                    color: Theme.text; font.pixelSize: 13; font.bold: true
                }
                ActionButton {
                    visible: dialog.needsLoaderStep && dialog.gameVersion
                    primary: false
                    label: "← Đổi phiên bản"
                    onClicked: dialog.gameVersion = ""
                }
            }
            Text {
                anchors { right: parent.right; top: parent.top; topMargin: 8 }
                text: "✕"; color: closeHover.hovered ? Theme.text : Theme.textMuted; font.pixelSize: 16
                HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: if (!bridge.busy) dialog.visible = false }
            }

            // Bước 1: lọc theo dòng lớn (1.21, 1.20, ...) rồi lưới phiên bản.
            Item {
                anchors { top: pickHeader.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: !(dialog.needsLoaderStep && dialog.gameVersion)

                Flow {
                    id: majorRow
                    anchors { left: parent.left; right: parent.right }
                    spacing: 6
                    Repeater {
                        model: ["Tất cả"].concat(dialog.majors)
                        Rectangle {
                            readonly property string majorKey: index === 0 ? "" : modelData
                            readonly property bool selected: dialog.majorFilter === majorKey
                            width: majorText.width + 18; height: 26; radius: 13
                            color: selected ? Theme.accentSoft : Theme.surfaceHigh
                            border.color: selected ? Theme.accent : Theme.border
                            Text { id: majorText; anchors.centerIn: parent; text: modelData
                                   color: selected ? Theme.accent : Theme.text; font.pixelSize: 11 }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: dialog.majorFilter = majorKey }
                        }
                    }
                }
                Text {
                    anchors { top: majorRow.bottom; topMargin: 20 }
                    visible: catalogBridge.releasedVersions.length === 0
                    text: catalogBridge.busy ? "Đang tải danh mục phiên bản..." : "Không tải được danh mục."
                    color: Theme.textMuted; font.pixelSize: 12
                }
                ActionButton {
                    anchors { top: majorRow.bottom; topMargin: 48 }
                    visible: catalogBridge.releasedVersions.length === 0 && !catalogBridge.busy
                    primary: false; label: "Thử lại"
                    onClicked: catalogBridge.loadReleasedVersions()
                }
                GridView {
                    anchors { top: majorRow.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                    clip: true
                    cellWidth: 112; cellHeight: 40
                    model: dialog.shownVersions
                    delegate: Item {
                        width: 112; height: 40
                        Rectangle {
                            id: versionCell
                            anchors { fill: parent; rightMargin: 8; bottomMargin: 8 }
                            readonly property bool selected: modelData.versionId === dialog.gameVersion
                            radius: 7
                            color: selected ? Theme.accentSoft : Theme.surfaceHigh
                            border.color: selected ? Theme.accent : Theme.border
                            Text { anchors.centerIn: parent; text: modelData.versionId
                                   color: versionCell.selected ? Theme.accent : Theme.text
                                   font.pixelSize: 12; font.family: "monospace" }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: dialog.pickGameVersion(modelData.versionId) }
                        }
                    }
                }
            }

            // Bước 2: danh sách loader Fabric, bản ổn định đánh dấu.
            Item {
                anchors { top: pickHeader.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: dialog.needsLoaderStep && dialog.gameVersion

                Text {
                    visible: catalogBridge.fabricLoaders.length === 0
                    text: catalogBridge.busy ? "Đang hỏi meta.fabricmc.net..." : "Không có bản loader cho phiên bản này."
                    color: Theme.textMuted; font.pixelSize: 12
                }
                ListView {
                    anchors.fill: parent
                    clip: true; spacing: 6
                    model: catalogBridge.fabricLoaders
                    delegate: Rectangle {
                        readonly property bool selected: modelData.loaderVersion === dialog.loaderVersion
                        width: ListView.view.width; height: 38; radius: 7
                        color: selected ? Theme.accentSoft : Theme.surfaceHigh
                        border.color: selected ? Theme.accent : Theme.border
                        Text {
                            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                            text: modelData.loaderVersion; color: Theme.text; font.pixelSize: 12; font.family: "monospace"
                        }
                        Rectangle {
                            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
                            visible: modelData.stable
                            width: stableText.width + 14; height: 18; radius: 4; color: Theme.accentDeep
                            Text { id: stableText; anchors.centerIn: parent; text: "ổn định"; color: "white"; font.pixelSize: 9 }
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: dialog.loaderVersion = modelData.loaderVersion }
                    }
                }
            }
        }
    }
}
