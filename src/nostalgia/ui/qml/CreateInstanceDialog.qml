import QtQuick
import QtQuick.Dialogs

/*
  Hộp thoại tạo bản chơi, hai cột, ba bước đánh số: ① kiểu bản chơi (thẻ Optimized nổi bật +
  lưới năm loader), ② phiên bản Minecraft ở cột phải, ③ tên. RAM và thư mục nằm sau nút
  "Thiết lập nâng cao" — chúng có mặc định đúng, để lộ ra thì chen vào giữa ba thứ phải quyết.

  Cột phải là các DÒNG phiên bản (26, 1.21, 1.20…) dạng thẻ có key art và số bản — bấm thẻ bung
  ra danh sách bản. Chọn loader khác Vanilla/Optimized thì hiện tiếp danh sách bản loader.
*/
Item {
    id: dialog
    visible: false
    z: 100

    property string loaderKind: "optimized"
    property string gameVersion: ""
    property string loaderVersion: ""
    property string expandedMajor: ""
    // Mở ra thì chỉ thấy phần quyết định; RAM và thư mục nằm sau nút này.
    property bool advancedOpen: false

    /* Optimized đứng ĐẦU bảng và có thẻ riêng ở trên lưới.

       Đây là lựa chọn đúng cho gần như mọi người mới: Fabric + Sodium cài sẵn, không phải
       hiểu "loader" là gì. Vanilla vẫn nằm ngay ô đầu lưới — dễ tìm, nhưng không còn là mặc
       định, vì mặc định cũ khiến người mới chơi bản chậm rồi tưởng máy yếu. */
    readonly property var loaderChoices: [
        { key: "optimized", label: "Optimized", icon: "assets/loaders/optimized.png" },
        { key: "vanilla",  label: "Vanilla",  icon: "assets/loaders/vanilla.png" },
        { key: "fabric",   label: "Fabric",   icon: "assets/loaders/fabric.png" },
        { key: "quilt",    label: "Quilt",    icon: "assets/loaders/quilt.png" },
        { key: "forge",    label: "Forge",    icon: "assets/loaders/forge.png" },
        { key: "neoforge", label: "NeoForge", icon: "assets/loaders/neoforge.png" }
    ]
    // Lưới bên dưới thẻ nổi bật: mọi loader ĐỀU hiện, không giấu cái nào trong "nâng cao".
    readonly property var gridChoices: loaderChoices.slice(1)
    // Optimized = modpack Fabulously Optimized: không có bước chọn bản loader, pack tự lo Fabric.
    readonly property bool isPreset: loaderKind === "optimized"
    readonly property bool needsLoaderStep: loaderKind !== "vanilla" && !isPreset
    // Danh mục lấy từ cầu nối MỘT lần mỗi khi nó đổi: mỗi lần đọc `catalogBridge.releasedVersions`
    // là Python chuyển cả trăm dict sang JS, nên vòng lặp `[i]` trên đó (16 thẻ cùng gọi) từng
    // làm mỗi cú bấm đứng ~200 ms. Tra dòng lớn của một bản qua bảng, không quét lại danh sách.
    readonly property var released: catalogBridge.releasedVersions
    readonly property var presetVersions: catalogBridge.presetGameVersions
    readonly property var majorIndex: {
        var byVersion = {};
        for (var i = 0; i < released.length; i++) byVersion[released[i].versionId] = released[i].major;
        return byVersion;
    }
    function presetSupports(versionId) {
        return !dialog.isPreset || dialog.presetVersions.length === 0 || dialog.presetVersions.indexOf(versionId) >= 0;
    }
    readonly property string loaderLabel: loaderChoices.find(function (c) { return c.key === dialog.loaderKind; }).label
    // Tên để trống thì tự đặt theo loader + phiên bản, như các launcher khác — bắt gõ tên là
    // một lý do "bấm Tạo không được" mà người dùng không đoán ra.
    readonly property string defaultName: loaderLabel + " " + gameVersion
    /* Nhãn nút nói rõ SẼ tạo ra cái gì — "Tạo bản chơi" không thôi thì người dùng không biết
       mình sắp nhận Vanilla hay Fabric hay bản tối ưu. */
    readonly property string createLabel: dialog.isPreset ? "Tạo bản chơi tối ưu"
                                                          : "Tạo bản chơi " + dialog.loaderLabel
    /* Phiên bản đang chọn nhưng Optimized không có gói cho nó.

       KHÔNG tự xoá lựa chọn như trước: đổi ngầm thứ người dùng vừa bấm là cách chắc nhất để
       họ tưởng mình bấm hụt. Giữ nguyên lựa chọn, khoá nút, và nói thẳng thiếu ở đâu. */
    readonly property bool versionUnsupported: gameVersion.length > 0 && !presetSupports(gameVersion)
    readonly property string missingStep: gameVersion.length === 0 ? "Chọn phiên bản Minecraft ở cột phải."
                                        : versionUnsupported
                                          ? "Bản tối ưu chưa có gói cho " + gameVersion
                                            + ". Chọn phiên bản khác, hoặc đổi sang Fabric."
                                        : (needsLoaderStep && loaderVersion.length === 0) ? "Chọn bản " + loaderLabel + " ở cột phải."
                                        : ""
    readonly property bool canCreate: missingStep.length === 0 && !bridge.busy
    // Các dòng lớn theo thứ tự mới → cũ, kèm số bản trong dòng.
    readonly property var majors: {
        var order = [], count = {};
        for (var i = 0; i < released.length; i++) {
            var major = released[i].major;
            if (!(major in count)) { count[major] = 0; order.push(major); }
            count[major] += 1;
        }
        return order.map(function (m) { return { major: m, count: count[m] }; });
    }
    // Dòng lớn của bản đã chọn, tính một lần cho mọi thẻ.
    readonly property string selectedMajor: majorOf(gameVersion)
    readonly property string previewMajor: selectedMajor || expandedMajor || (majors.length ? majors[0].major : "")

    function majorOf(versionId) {
        return dialog.majorIndex[versionId] || "";
    }
    // Dòng có key art riêng; dòng khác (1.7 trở về trước, snapshot lạ) dùng ảnh Java Edition cổ điển.
    readonly property var knownArt: ["26", "1.21", "1.20", "1.19", "1.18", "1.17", "1.16", "1.15", "1.14",
                                     "1.13", "1.12", "1.11", "1.10", "1.9", "1.8"]
    function artFor(major) {
        return knownArt.indexOf(major) >= 0 ? "assets/keyart/" + major + ".jpg" : "assets/keyart/old.jpg";
    }
    function versionsOf(major) {
        return dialog.released.filter(function (r) { return r.major === major; });
    }
    // Thư mục chơi riêng (URL file:// từ FolderDialog); rỗng = theo cài đặt / mặc định.
    property string gameDirUrl: ""
    readonly property string gameDirPath: gameDirUrl ? decodeURIComponent(String(gameDirUrl).replace(/^file:\/\//, "")) : ""
    function openDialog() {
        dialog.loaderKind = "optimized";
        dialog.gameVersion = ""; dialog.loaderVersion = ""; dialog.expandedMajor = ""; dialog.gameDirUrl = "";
        dialog.advancedOpen = false;
        nameField.text = ""; heapField.text = "";
        dialog.visible = true;
        notifier.playUi("open");
        if (dialog.released.length === 0) catalogBridge.loadReleasedVersions();
        // Mở ra là đã ở Optimized, nên danh sách bản được hỗ trợ phải có ngay — không có thì
        // mọi phiên bản trông như "được hỗ trợ" cho tới lúc bấm.
        catalogBridge.loadPresetVersions();
    }
    function close() {
        notifier.playUi("back");
        dialog.visible = false;
    }
    function pickGameVersion(versionId) {
        notifier.playUi("select");
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
        onClicked: if (!bridge.busy) dialog.close()
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }

    Rectangle {
        id: box
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 1120)
        height: Math.min(parent.height - 20, 760)
        radius: Theme.radius
        color: Theme.surface
        // Nét mực tối 2 px như Panel.qml — hộp thoại phải cùng ngôn ngữ hình khối với thẻ.
        border.color: Qt.darker(Theme.background, 1.7)
        border.width: 2
        scale: dialog.visible ? 1 : 0.96
        Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent }

        // ----- cột trái: form (cuộn được khi cửa sổ thấp) -----
        Item {
            id: form
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 24 }
            width: Math.min(300, box.width * 0.35)

            Flickable {
                id: formFlick
                anchors.fill: parent
                contentWidth: width
                contentHeight: formColumn.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.VerticalFlick

                Column {
                    id: formColumn
                    width: formFlick.width
                    spacing: 14

                    Column {
                        spacing: 2
                        Text { text: "Tạo bản chơi"; color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true }
                        Text {
                            text: (dialog.isPreset ? "Tối ưu hiệu năng" : dialog.loaderLabel)
                                  + (dialog.gameVersion ? "  ·  " + dialog.gameVersion : "")
                                  + (dialog.loaderVersion ? "  ·  " + dialog.loaderVersion : "")
                            color: Theme.accent; font.pixelSize: Theme.fontBody
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

                    /* Bước 1 của ba bước: chọn KIỂU bản chơi.

                       Thẻ Optimized nằm riêng phía trên lưới, rộng bằng cả cột và có nhãn
                       "Đề xuất" — không phải một ô ngang hàng trong lưới, vì ngang hàng thì
                       nó chỉ là một lựa chọn thứ sáu và người mới vẫn bấm Vanilla. */
                    Column {
                        spacing: 8; width: parent.width
                        Text { text: "① KIỂU BẢN CHƠI"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }

                        Rectangle {
                            objectName: "optimizedCard"
                            readonly property bool selected: dialog.isPreset
                            width: parent.width; height: 74; radius: Theme.radiusSmall
                            color: selected ? Theme.accentSoft : Theme.surfaceHigh
                            border.color: selected ? Theme.accent : Theme.border
                            border.width: 2
                            Behavior on color { ColorAnimation { duration: Theme.quick } }

                            Image {
                                id: optIcon
                                anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                                width: 34; height: 34; source: "assets/loaders/optimized.png"
                                fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                            }
                            Column {
                                anchors { left: optIcon.right; leftMargin: 12; right: parent.right; rightMargin: 12
                                          verticalCenter: parent.verticalCenter }
                                spacing: 3
                                Row {
                                    spacing: 8
                                    Text { text: "Tối ưu hiệu năng"; color: Theme.text
                                           font.pixelSize: Theme.fontHeading; font.bold: true }
                                    Rectangle {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: recommendText.width + 12; height: 17; radius: 0
                                        color: Theme.accent
                                        Text { id: recommendText; anchors.centerIn: parent; text: "ĐỀ XUẤT"
                                               color: "#11151c"; font.pixelSize: Theme.fontLabel
                                               font.bold: true; font.letterSpacing: 0.8 }
                                    }
                                }
                                Text {
                                    width: parent.width
                                    text: "Cài sẵn Fabulously Optimized, gồm Fabric và các mod tối ưu"
                                    color: Theme.textMuted; font.pixelSize: Theme.fontBody; wrapMode: Text.WordWrap
                                }
                            }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler {
                                onTapped: {
                                    if (!dialog.isPreset) notifier.playUi("nav");
                                    dialog.loaderKind = "optimized";
                                    dialog.loaderVersion = "";
                                    catalogBridge.loadPresetVersions();
                                }
                            }
                        }

                        Grid {
                            id: loaderGrid
                            objectName: "loaderRow"
                            columns: parent.width < 280 ? 2 : 3; spacing: 8
                            Repeater {
                                model: dialog.gridChoices
                                Rectangle {
                                    readonly property bool selected: modelData.key === dialog.loaderKind
                                    width: Math.min(94, (form.width - (loaderGrid.columns - 1) * 8) / loaderGrid.columns); height: 66; radius: Theme.radiusSmall
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
                                            font.pixelSize: Theme.fontBody; font.bold: selected
                                        }
                                    }
                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    TapHandler {
                                        onTapped: {
                                            if (!selected) notifier.playUi("nav");
                                            dialog.loaderKind = modelData.key;
                                            dialog.loaderVersion = "";
                                            if (dialog.isPreset) catalogBridge.loadPresetVersions();
                                            // KHÔNG xoá `gameVersion` khi bản không được Optimized hỗ trợ.
                                            // Xoá ngầm thì người dùng thấy lựa chọn của mình biến mất mà không
                                            // ai nói vì sao; nay giữ nguyên và báo ở dòng "Còn thiếu".
                                            if (dialog.needsLoaderStep && dialog.gameVersion)
                                                catalogBridge.loadLoaderVersions(dialog.loaderKind, dialog.gameVersion);
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Column {
                        spacing: 5; width: parent.width
                        Text { text: "③ TÊN"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                        TextField {
                            id: nameField; width: parent.width
                            placeholder: dialog.gameVersion ? dialog.defaultName : "Để trống = tự động"
                        }
                    }

                    /* Thiết lập nâng cao: RAM và thư mục game.

                       Hai thứ này có mặc định đúng cho gần như mọi người, và để lộ ra thì
                       chúng chen vào đúng giữa ba bước cần quyết định — người mới không phân
                       biệt được "thứ phải chọn" với "thứ có thể bỏ qua". Mặc định GIỮ NGUYÊN,
                       chỉ đổi chỗ đứng. */
                    Rectangle {
                        objectName: "advancedToggle"
                        width: parent.width; height: 32; radius: Theme.radiusSmall
                        color: advancedHover.hovered ? Theme.surfaceHigh : "transparent"
                        border.color: Theme.border
                        Text {
                            anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                            text: (dialog.advancedOpen ? "▴  " : "▾  ") + "Thiết lập nâng cao"
                            color: Theme.textMuted; font.pixelSize: Theme.fontBody
                        }
                        HoverHandler { id: advancedHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: dialog.advancedOpen = !dialog.advancedOpen }
                    }
                    Column {
                        objectName: "advancedBox"
                        width: parent.width; spacing: 10
                        visible: dialog.advancedOpen

                        Row {
                            spacing: 10
                            Text { anchors.verticalCenter: parent.verticalCenter; text: "RAM (MB)"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                            TextField { id: heapField; width: 110; placeholder: "mặc định" }
                        }

                        Column {
                            spacing: 5; width: parent.width
                            Text { text: "THƯ MỤC GAME"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel; font.letterSpacing: 1.2 }
                            // Bấm để chọn ổ khác cho mods/saves của bản chơi này (kho chung vẫn ở data_dir).
                            Rectangle {
                                objectName: "gameDirPicker"
                                width: parent.width; height: 34; radius: Theme.radiusSmall
                                color: Theme.surfaceHigh; border.color: folderHover.hovered ? Theme.accent : Theme.border
                                Text {
                                    anchors { left: parent.left; leftMargin: 10; right: clearFolder.left; rightMargin: 6; verticalCenter: parent.verticalCenter }
                                    text: dialog.gameDirUrl ? dialog.gameDirPath
                                          : (settingsBridge.defaultGameDirRoot ? "Mặc định: " + settingsBridge.defaultGameDirRoot + "/…" : "Mặc định trong instances/ — bấm để chọn ổ khác")
                                    elide: Text.ElideMiddle
                                    color: dialog.gameDirUrl ? Theme.text : Theme.textMuted; font.pixelSize: Theme.fontBody
                                }
                                Text {
                                    id: clearFolder
                                    visible: dialog.gameDirUrl !== ""
                                    anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                                    text: "✕"; color: Theme.textMuted; font.pixelSize: Theme.fontBody
                                    TapHandler { onTapped: dialog.gameDirUrl = "" }
                                }
                                HoverHandler { id: folderHover; cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: folderPicker.open() }
                            }
                        }
                    }

                    // --- Khu vực dưới cùng: thông báo + nút tạo (nằm trong cùng Column để cuộn được) ---
                    Item { width: 1; height: 8 }  // spacer

                    Text {
                        visible: !bridge.busy && dialog.missingStep.length > 0
                        width: parent.width
                        text: "Còn thiếu: " + dialog.missingStep
                        color: Theme.accent; font.pixelSize: Theme.fontBody; wrapMode: Text.WordWrap
                    }
                    Text {
                        visible: !bridge.busy && dialog.isPreset
                        width: parent.width
                        text: "Fabulously Optimized: Fabric + Sodium và các mod tối ưu, cài sẵn từ Modrinth. Bản không có gói sẽ mờ đi."
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody; wrapMode: Text.WordWrap
                    }
                    // Lối thoát ngay tại chỗ tắc: bản đã chọn không có gói tối ưu thì đổi sang
                    // Fabric là xong, không phải quay lên lưới tìm.
                    ActionButton {
                        objectName: "switchToFabric"
                        visible: !bridge.busy && dialog.versionUnsupported
                        width: parent.width
                        primary: false
                        label: "Dùng Fabric cho " + dialog.gameVersion
                        onClicked: {
                            dialog.loaderKind = "fabric";
                            dialog.loaderVersion = "";
                            catalogBridge.loadLoaderVersions("fabric", dialog.gameVersion);
                        }
                    }
                    Text {
                        visible: !bridge.busy && (dialog.loaderKind === "forge" || dialog.loaderKind === "neoforge")
                        width: parent.width
                        text: "Forge/NeoForge cài bằng installer chính thức; có thể mất vài phút."
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody; wrapMode: Text.WordWrap
                    }
                    Text {
                        visible: bridge.busy
                        width: parent.width
                        text: bridge.progressText
                        color: Theme.textMuted; font.pixelSize: Theme.fontBody; elide: Text.ElideRight
                    }
                    ActionButton {
                        width: parent.width
                        height: 44
                        label: bridge.busy ? "Đang cài..." : dialog.createLabel
                        clickable: dialog.canCreate
                        onClicked: catalogBridge.createInstance(nameField.text.trim() || dialog.defaultName,
                                                                dialog.gameVersion, dialog.loaderKind,
                                                                dialog.loaderVersion, parseInt(heapField.text) || 0,
                                                                dialog.gameDirUrl)
                    }
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
                          : "② CHỌN PHIÊN BẢN MINECRAFT"
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody; font.bold: true; font.letterSpacing: 1.2
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
                text: "✕"; color: closeHover.hovered ? Theme.text : Theme.textMuted; font.pixelSize: Theme.fontHeading
                HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: if (!bridge.busy) dialog.close() }
            }

            // Bước 1: thẻ theo dòng, bung ra danh sách bản.
            Item {
                anchors { top: pickHeader.bottom; topMargin: 12; left: parent.left; right: parent.right; bottom: parent.bottom }
                visible: !(dialog.needsLoaderStep && dialog.gameVersion)

                Text {
                    visible: dialog.released.length === 0
                    text: catalogBridge.busy ? "Đang tải danh mục phiên bản..." : "Không tải được danh mục."
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
                ActionButton {
                    y: 30
                    visible: dialog.released.length === 0 && !catalogBridge.busy
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
                        // Thẻ vẽ ĐÚNG tỉ lệ key art 2,56:1 để không cắt mất logo hay nhân vật; các
                        // phiên bản con trượt xuống bên dưới ảnh với hoạt ảnh, không nhảy phắt.
                        readonly property int artHeight: Math.max(150, Math.min(300, Math.round(width / 2.56)))
                        // Thẻ "sáng" khi đang bung hoặc chứa phiên bản đã chọn; thẻ khác nằm tối mờ
                        // trong ô. Thẻ sáng có quầng sáng quanh viền, bóng đổ và nhấc lên khỏi ô.
                        readonly property bool lit: expanded || dialog.selectedMajor === modelData.major
                        height: artHeight + 20 + (expanded ? chips.implicitHeight + 14 : 0)
                        Behavior on height { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }

                        Item {
                            id: artBlock
                            anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 8; rightMargin: 8 }
                            anchors.topMargin: card.lit ? 6 : 12
                            height: card.artHeight
                            scale: card.lit ? 1.015 : 1
                            transformOrigin: Item.Center
                            Behavior on anchors.topMargin { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
                            Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }

                            // Bóng đổ dưới thẻ đã nhấc lên.
                            Rectangle {
                                x: 0; y: 7; width: parent.width; height: parent.height
                                radius: Theme.radiusSmall + 2; color: "#000000"
                                opacity: card.lit ? 0.45 : 0
                                Behavior on opacity { NumberAnimation { duration: Theme.normal } }
                            }
                            // Quầng sáng: ba vòng viền màu accent mờ dần ra ngoài, không cần shader.
                            Rectangle {
                                anchors.fill: parent; anchors.margins: -9
                                radius: Theme.radiusSmall + 9; color: "transparent"
                                border.width: 4; border.color: Theme.accent
                                opacity: card.lit ? 0.1 : 0
                                Behavior on opacity { NumberAnimation { duration: Theme.normal } }
                            }
                            Rectangle {
                                anchors.fill: parent; anchors.margins: -5
                                radius: Theme.radiusSmall + 5; color: "transparent"
                                border.width: 5; border.color: Theme.accent
                                opacity: card.lit ? 0.22 : 0
                                Behavior on opacity { NumberAnimation { duration: Theme.normal } }
                            }
                            Rectangle {
                                anchors.fill: parent; anchors.margins: -2
                                radius: Theme.radiusSmall + 2; color: "transparent"
                                border.width: 2; border.color: Theme.accent
                                opacity: card.lit ? 0.6 : 0
                                Behavior on opacity { NumberAnimation { duration: Theme.normal } }
                            }

                            Rectangle {
                                id: art
                                anchors.fill: parent
                                radius: Theme.radiusSmall; clip: true
                                color: Theme.surfaceHigh
                                border.color: card.lit ? Theme.accent : Theme.border
                                Behavior on border.color { ColorAnimation { duration: Theme.normal } }
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
                                // Lớp tối phủ thẻ chưa chọn; rê chuột vào thì hé sáng, chọn thì bỏ hẳn.
                                Rectangle {
                                    anchors.fill: parent; color: "#06090c"
                                    opacity: card.lit ? 0 : (artHover.hovered ? 0.3 : 0.55)
                                    Behavior on opacity { NumberAnimation { duration: Theme.normal } }
                                }
                                Column {
                                    anchors { left: parent.left; leftMargin: 18; bottom: parent.bottom; bottomMargin: 14 }
                                    opacity: card.lit ? 1 : 0.75
                                    Behavior on opacity { NumberAnimation { duration: Theme.normal } }
                                    Text { text: modelData.major; color: Theme.text; font.pixelSize: Theme.fontHero; font.bold: true
                                           style: Text.Raised; styleColor: "#80000000" }
                                    Text { text: modelData.count + " phiên bản"; color: Theme.text; font.pixelSize: Theme.fontBody; opacity: 0.85 }
                                }
                                Text {
                                    anchors { right: parent.right; rightMargin: 16; bottom: parent.bottom; bottomMargin: 12 }
                                    text: card.expanded ? "▲" : "▼"; color: Theme.text; font.pixelSize: Theme.fontBody; opacity: 0.8
                                }
                                HoverHandler { id: artHover; cursorShape: Qt.PointingHandCursor }
                                TapHandler {
                                    onTapped: {
                                        notifier.playUi(card.expanded ? "back" : "open");
                                        dialog.expandedMajor = card.expanded ? "" : modelData.major;
                                        if (!card.expanded) majorList.positionViewAtIndex(index, ListView.Beginning);
                                    }
                                }
                            }
                        }
                        // Khung cắt riêng cho các nút phiên bản: lúc thẻ đang trượt mở, nút không tràn
                        // sang thẻ dưới; còn quầng sáng của ảnh thì không bị cắt.
                        Item {
                            clip: true
                            anchors { left: parent.left; right: parent.right; top: artBlock.bottom; topMargin: 10; bottom: parent.bottom }
                            Flow {
                                id: chips
                                anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 8; rightMargin: 8 }
                                spacing: 8
                                opacity: card.expanded ? 1 : 0
                                enabled: card.expanded
                                Behavior on opacity { NumberAnimation { duration: Theme.normal } }
                                Repeater {
                                    model: card.versions
                                    // Nút phiên bản kiểu khối Minecraft như trang chủ: khối đá, chọn thì thành khối cỏ.
                                    Item {
                                        id: versionCell
                                        readonly property bool selected: modelData.versionId === dialog.gameVersion
                                        readonly property bool supported: dialog.presetSupports(modelData.versionId)
                                        readonly property int edge: 3
                                        width: Math.max(78, versionText.width + 26); height: 34
                                        /* Bản không có gói tối ưu: mờ đi nhưng VẪN bấm được.

                                           Khoá hẳn thì người dùng bấm mãi không ăn mà không
                                           biết vì sao. Bấm được thì dòng "Còn thiếu" nói rõ
                                           lý do và đưa luôn nút đổi sang Fabric. */
                                        opacity: supported ? 1 : 0.45
                                        Rectangle { anchors.fill: parent; color: "#1e1e1f" }
                                        Rectangle {
                                            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 2 }
                                            height: parent.height - 4
                                            // Màu của tab, không phải sắc lục viết cứng: nút phiên bản
                                            // và tiêu đề trang nằm cùng màn hình.
                                            color: versionCell.selected ? Qt.darker(Theme.accent, 2.4) : "#2e2a25"
                                        }
                                        Rectangle {
                                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 2 }
                                            anchors.topMargin: versionPress.pressed ? 4 : 2
                                            height: parent.height - 4 - versionCell.edge + (versionPress.pressed ? 2 : 0)
                                            color: versionCell.selected
                                                   ? (versionHover.hovered ? Qt.lighter(Qt.darker(Theme.accent, 1.35), 1.22)
                                                                           : Qt.darker(Theme.accent, 1.35))
                                                   : (versionHover.hovered ? "#5a5247" : "#4a443c")
                                            Behavior on color { ColorAnimation { duration: Theme.quick } }
                                            Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top }
                                                        height: 2; color: versionCell.selected ? "#66ffffff" : "#33ffffff" }
                                            Text { id: versionText; anchors.centerIn: parent; text: modelData.versionId
                                                   color: versionCell.selected ? "white" : "#e8dcc8"
                                                   font.pixelSize: Theme.fontBody; font.bold: true
                                                   style: Text.Raised; styleColor: "#40000000" }
                                        }
                                        HoverHandler { id: versionHover; cursorShape: Qt.PointingHandCursor }
                                        TapHandler { id: versionPress; onTapped: dialog.pickGameVersion(modelData.versionId) }
                                    }
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
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
                ListView {
                    anchors.fill: parent
                    clip: true; spacing: 6
                    model: catalogBridge.loaderVersions
                    delegate: Rectangle {
                        readonly property bool selected: modelData.loaderVersion === dialog.loaderVersion
                        width: ListView.view.width; height: 38; radius: 0
                        color: selected ? Theme.accentSoft : Theme.surfaceHigh
                        border.color: selected ? Theme.accent : Theme.border
                        Text {
                            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                            text: modelData.loaderVersion; color: Theme.text; font.pixelSize: Theme.fontBody; font.family: "monospace"
                        }
                        Rectangle {
                            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
                            visible: modelData.stable
                            width: stableText.width + 14; height: 18; radius: 0; color: Theme.accentDeep
                            Text { id: stableText; anchors.centerIn: parent; text: "ổn định"; color: "white"; font.pixelSize: Theme.fontLabel }
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: dialog.loaderVersion = modelData.loaderVersion }
                    }
                }
            }
        }
    }

    FolderDialog {
        id: folderPicker
        title: "Chọn thư mục chơi cho bản chơi này"
        onAccepted: dialog.gameDirUrl = selectedFolder.toString()
    }
}
