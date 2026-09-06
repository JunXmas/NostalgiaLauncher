import QtQuick

/*
  Hộp thoại tạo bản chơi, hai cột theo bản mẫu: trái là form (ảnh minh hoạ của dòng đang chọn,
  tên, thư mục, lưới loader có icon, RAM, nút tạo); phải là các DÒNG phiên bản (26, 1.21, 1.20…)
  dạng thẻ có key art và số bản — bấm thẻ bung ra danh sách bản để chọn. Chọn loader khác
  Vanilla thì bước 2 hiện danh sách bản loader thay cho các thẻ.
*/
Item {
    id: dialog
    visible: false
    z: 100

    property string loaderKind: "vanilla"
    property string gameVersion: ""
    property string loaderVersion: ""
    property string expandedMajor: ""
    readonly property var loaderChoices: [
        { key: "vanilla",  label: "Vanilla",  icon: "assets/loaders/vanilla.png" },
        { key: "fabric",   label: "Fabric",   icon: "assets/loaders/fabric.png" },
        { key: "quilt",    label: "Quilt",    icon: "assets/loaders/quilt.png" },
        { key: "forge",    label: "Forge",    icon: "assets/loaders/forge.png" },
        { key: "neoforge", label: "NeoForge", icon: "assets/loaders/neoforge.png" }
    ]
    readonly property bool needsLoaderStep: loaderKind !== "vanilla"
    readonly property string loaderLabel: loaderChoices.find(function (c) { return c.key === dialog.loaderKind; }).label
    // Tên để trống thì tự đặt theo loader + phiên bản, như các launcher khác — bắt gõ tên là
    // một lý do "bấm Tạo không được" mà người dùng không đoán ra.
    readonly property string defaultName: loaderLabel + " " + gameVersion
    readonly property string missingStep: gameVersion.length === 0 ? "Chọn phiên bản Minecraft ở cột phải."
                                        : (needsLoaderStep && loaderVersion.length === 0) ? "Chọn bản " + loaderLabel + " ở cột phải."
                                        : ""
    readonly property bool canCreate: missingStep.length === 0 && !bridge.busy
    // Các dòng lớn theo thứ tự mới → cũ, kèm số bản trong dòng.
    readonly property var majors: {
        var order = [], count = {};
        for (var i = 0; i < catalogBridge.releasedVersions.length; i++) {
            var major = catalogBridge.releasedVersions[i].major;
            if (!(major in count)) { count[major] = 0; order.push(major); }
            count[major] += 1;
        }
        return order.map(function (m) { return { major: m, count: count[m] }; });
    }
    readonly property string previewMajor: gameVersion ? majorOf(gameVersion) : (expandedMajor || (majors.length ? majors[0].major : ""))

    function majorOf(versionId) {
        for (var i = 0; i < catalogBridge.releasedVersions.length; i++)
            if (catalogBridge.releasedVersions[i].versionId === versionId) return catalogBridge.releasedVersions[i].major;
        return "";
    }
    // Dòng có key art riêng; dòng khác (1.7 trở về trước, snapshot lạ) dùng ảnh Java Edition cổ điển.
    readonly property var knownArt: ["26", "1.21", "1.20", "1.19", "1.18", "1.17", "1.16", "1.15", "1.14",
                                     "1.13", "1.12", "1.11", "1.10", "1.9", "1.8"]
    function artFor(major) {
        return knownArt.indexOf(major) >= 0 ? "assets/keyart/" + major + ".jpg" : "assets/keyart/old.jpg";
    }
    function versionsOf(major) {
        return catalogBridge.releasedVersions.filter(function (r) { return r.major === major; });
    }
    function openDialog() {
        dialog.gameVersion = ""; dialog.loaderVersion = ""; dialog.expandedMajor = "";
        nameField.text = ""; heapField.text = "";
        dialog.visible = true;
        if (catalogBridge.releasedVersions.length === 0) catalogBridge.loadReleasedVersions();
    }
    function pickGameVersion(versionId) {
        dialog.gameVersion = versionId;
        dialog.loaderVersion = "";
        if (dialog.needsLoaderStep) catalogBridge.loadLoaderVersions(dialog.loaderKind, versionId);
    }

    Connections {
        target: catalogBridge
        function onCreated(instanceId) { dialog.visible = false; }
    }

    // Màn tối phía sau; bấm ra ngoài là đóng. MouseArea chứ không TapHandler: TapHandler không
    // nuốt sự kiện nên bấm nút BÊN TRONG hộp cũng lọt xuống đây (lỗi thật).
    MouseArea {
        anchors.fill: parent
        onClicked: if (!bridge.busy) dialog.visible = false
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }

    Rectangle {
        id: box
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 1120)
        height: Math.min(parent.height - 40, 760)
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        scale: dialog.visible ? 1 : 0.96
        Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent }

        // ----- cột trái: form -----
        Item {
            id: form
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 24 }
            width: 300

            Column {
                id: formTop
                anchors { left: parent.left; right: parent.right; top: parent.top }
                spacing: 14

                Column {
                    spacing: 2
                    Text { text: "Tạo bản chơi"; color: Theme.text; font.pixelSize: 18; font.bold: true }
                    Text {
                        text: dialog.loaderLabel + (dialog.gameVersion ? "  ·  " + dialog.gameVersion : "")
                              + (dialog.loaderVersion ? "  ·  " + dialog.loaderVersion : "")
                        color: Theme.accent; font.pixelSize: 11
                    }
                }

                // Ảnh minh hoạ của dòng đang chọn (hoặc dòng đang bung).
                Rectangle {
                    width: parent.width; height: Math.round(width / 2.56); radius: Theme.radiusSmall; clip: true
                    color: Theme.surfaceHigh; border.color: Theme.border
                    Image {
                        id: previewArt
                        anchors.fill: parent; anchors.margins: 1
                        source: dialog.artFor(dialog.previewMajor)
                        fillMode: Image.PreserveAspectCrop; asynchronous: true
                    }
                }

                Column {
                    spacing: 5; width: parent.width
                    Text { text: "TÊN"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    TextField {
                        id: nameField; width: parent.width
                        placeholder: dialog.gameVersion ? dialog.defaultName : "Để trống = tự động"
                    }
                }

                Column {
                    spacing: 5; width: parent.width
                    Text { text: "THƯ MỤC GAME"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    Rectangle {
                        width: parent.width; height: 34; radius: Theme.radiusSmall
                        color: Theme.surfaceHigh; border.color: Theme.border
                        Text {
                            anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                            text: "Mặc định trong instances/"; color: Theme.textMuted; font.pixelSize: 12
                        }
                    }
                }

                Column {
                    spacing: 5; width: parent.width
                    Text { text: "LOADER"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    Grid {
                        objectName: "loaderRow"
                        columns: 3; spacing: 8
                        Repeater {
                            model: dialog.loaderChoices
                            Rectangle {
                                readonly property bool selected: modelData.key === dialog.loaderKind
                                width: 94; height: 66; radius: Theme.radiusSmall
                                color: selected ? Theme.accentSoft : Theme.surfaceHigh
                                border.color: selected ? Theme.accent : Theme.border
                                border.width: 1
                                Column {
                                    anchors.centerIn: parent; spacing: 5
                                    Image {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        width: 26; height: 26; source: modelData.icon
                                        fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                                    }
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: modelData.label; color: selected ? Theme.accent : Theme.text
                                        font.pixelSize: 11; font.bold: selected
                                    }
                                }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                TapHandler {
                                    onTapped: {
                                        dialog.loaderKind = modelData.key;
                                        dialog.loaderVersion = "";
                                        if (dialog.needsLoaderStep && dialog.gameVersion)
                                            catalogBridge.loadLoaderVersions(dialog.loaderKind, dialog.gameVersion);
                                    }
                                }
                            }
                        }
                    }
                }

                Row {
                    spacing: 10
                    Text { anchors.verticalCenter: parent.verticalCenter; text: "RAM (MB)"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    TextField { id: heapField; width: 110; placeholder: "mặc định" }
                }
            }

            Column {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                spacing: 8
                Text {
                    visible: !bridge.busy && dialog.missingStep.length > 0
                    width: parent.width
                    text: "Còn thiếu: " + dialog.missingStep
                    color: Theme.accent; font.pixelSize: 11; wrapMode: Text.WordWrap
                }
                Text {
                    visible: !bridge.busy && (dialog.loaderKind === "forge" || dialog.loaderKind === "neoforge")
                    width: parent.width
                    text: "Forge/NeoForge cài bằng installer chính thức; có thể mất vài phút."
                    color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap
                }
                Text {
                    visible: bridge.busy
                    width: parent.width
                    text: bridge.progressText
                    color: Theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight
                }
                ActionButton {
                    width: parent.width
                    height: 44
                    label: bridge.busy ? "Đang cài..." : "Tạo bản chơi " + dialog.loaderLabel
                    clickable: dialog.canCreate
                    onClicked: catalogBridge.createInstance(nameField.text.trim() || dialog.defaultName,
                                                            dialog.gameVersion, dialog.loaderKind,
                                                            dialog.loaderVersion, parseInt(heapField.text) || 0)
                }
            }
        }

        Rectangle { x: form.x + form.width + 20; y: 0; width: 1; height: box.height; color: Theme.border }

        // ----- cột phải: chọn dòng và phiên bản -----
        Item {
            anchors { left: form.right; leftMargin: 40; right: parent.right; top: parent.top; bottom: parent.bottom; margins: 24 }

            Row {
                id: pickHeader
                anchors { left: parent.left; right: parent.right }
                height: 30
                spacing: 12
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: dialog.needsLoaderStep && dialog.gameVersion
                          ? "CHỌN PHIÊN BẢN " + dialog.loaderLabel.toUpperCase() + " CHO " + dialog.gameVersion
                          : "CHỌN PHIÊN BẢN MINECRAFT"
                    color: Theme.textMuted; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2
                }
                ActionButton {
                    visible: dialog.needsLoaderStep && dialog.gameVersion
                    primary: false
                    label: "← Đổi phiên bản"
                    onClicked: dialog.gameVersion = ""
                }
            }
            Text {
                anchors { right: parent.right; top: parent.top; topMargin: 4 }
                text: "✕"; color: closeHover.hovered ? Theme.text : Theme.textMuted; font.pixelSize: 16
                HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: if (!bridge.busy) dialog.visible = false }
            }

            // Bước 1: thẻ theo dòng, bung ra danh sách bản.
            Item {
                anchors { top: pickHeader.bottom; topMargin: 12; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: !(dialog.needsLoaderStep && dialog.gameVersion)

                Text {
                    visible: catalogBridge.releasedVersions.length === 0
                    text: catalogBridge.busy ? "Đang tải danh mục phiên bản..." : "Không tải được danh mục."
                    color: Theme.textMuted; font.pixelSize: 12
                }
                ActionButton {
                    y: 30
                    visible: catalogBridge.releasedVersions.length === 0 && !catalogBridge.busy
                    primary: false; label: "Thử lại"
                    onClicked: catalogBridge.loadReleasedVersions()
                }
                ListView {
                    id: majorList
                    anchors.fill: parent
                    clip: true; spacing: 10
                    model: dialog.majors
                    delegate: Item {
                        id: card
                        readonly property bool expanded: dialog.expandedMajor === modelData.major
                        readonly property var versions: expanded ? dialog.versionsOf(modelData.major) : []
                        width: ListView.view.width
                        // Thẻ cao theo bề ngang để key art (2,56:1) không bị cắt quá nửa.
                        readonly property int artHeight: Math.max(150, Math.min(210, Math.round(width / 3.1)))
                        height: artHeight + (expanded ? chips.height + 12 : 0)

                        Rectangle {
                            id: art
                            anchors { left: parent.left; right: parent.right; top: parent.top }
                            height: card.artHeight; radius: Theme.radiusSmall; clip: true
                            color: Theme.surfaceHigh
                            border.color: card.expanded || dialog.majorOf(dialog.gameVersion) === modelData.major ? Theme.accent : Theme.border
                            Image {
                                anchors.fill: parent; anchors.margins: 1
                                source: dialog.artFor(modelData.major)
                                fillMode: Image.PreserveAspectCrop; asynchronous: true
                            }
                            Rectangle {
                                anchors.fill: parent
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: "#cc07100a" }
                                    GradientStop { position: 0.45; color: "#5507100a" }
                                    GradientStop { position: 1.0; color: "#1a07100a" }
                                }
                            }
                            Column {
                                anchors { left: parent.left; leftMargin: 18; bottom: parent.bottom; bottomMargin: 14 }
                                Text { text: modelData.major; color: Theme.text; font.pixelSize: 28; font.bold: true
                                       style: Text.Raised; styleColor: "#80000000" }
                                Text { text: modelData.count + " phiên bản"; color: Theme.text; font.pixelSize: 12; opacity: 0.85 }
                            }
                            Text {
                                anchors { right: parent.right; rightMargin: 16; bottom: parent.bottom; bottomMargin: 12 }
                                text: card.expanded ? "▲" : "▼"; color: Theme.text; font.pixelSize: 12; opacity: 0.8
                            }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler {
                                onTapped: {
                                    dialog.expandedMajor = card.expanded ? "" : modelData.major;
                                    if (!card.expanded) majorList.positionViewAtIndex(index, ListView.Beginning);
                                }
                            }
                        }
                        Flow {
                            id: chips
                            anchors { left: parent.left; right: parent.right; top: art.bottom; topMargin: 8 }
                            spacing: 6
                            visible: card.expanded
                            Repeater {
                                model: card.versions
                                Rectangle {
                                    id: versionCell
                                    readonly property bool selected: modelData.versionId === dialog.gameVersion
                                    width: Math.max(72, versionText.width + 22); height: 30; radius: 7
                                    color: selected ? Theme.accentSoft : Theme.surfaceHigh
                                    border.color: selected ? Theme.accent : Theme.border
                                    Text { id: versionText; anchors.centerIn: parent; text: modelData.versionId
                                           color: versionCell.selected ? Theme.accent : Theme.text
                                           font.pixelSize: 12; font.family: "monospace" }
                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: dialog.pickGameVersion(modelData.versionId) }
                                }
                            }
                        }
                    }
                }
            }

            // Bước 2: danh sách bản loader; bản ổn định / recommended được đánh dấu.
            Item {
                anchors { top: pickHeader.bottom; topMargin: 12; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: dialog.needsLoaderStep && dialog.gameVersion

                Text {
                    visible: catalogBridge.loaderVersions.length === 0
                    text: catalogBridge.busy ? "Đang lấy danh sách bản loader..." : "Không có bản loader cho phiên bản này."
                    color: Theme.textMuted; font.pixelSize: 12
                }
                ListView {
                    anchors.fill: parent
                    clip: true; spacing: 6
                    model: catalogBridge.loaderVersions
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
