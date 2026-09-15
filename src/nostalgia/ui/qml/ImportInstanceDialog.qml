import QtQuick
import QtQuick.Dialogs

/*
  Hộp thoại nhập bản chơi: ba tab — file .mrpack, launcher khác trên máy, mã phòng.
  Kết nối với ImportBridge (MYLA-31) qua bốn signal: onScanDone, onImportProgress,
  onImportDone, onImportError. Chiều rộng cố định 520 px, không resize.
*/
Item {
    id: dialog
    visible: false
    z: 100

    // Trạng thái dùng chung cho cả ba tab.
    property int tabIndex: 0
    property string errorText: ""
    property bool importing: false
    property real progress: 0        // 0–1
    property int progressCurrent: 0  // file/mod hiện tại
    property int progressTotal: 0    // tổng file/mod

    // Tab 1: file .mrpack
    property string mrpackPath: ""
    property string mrpackName: ""
    property string mrpackMcVersion: ""
    property string mrpackLoader: ""
    property int    mrpackFileCount: 0
    readonly property bool mrpackReady: mrpackPath.length > 0 && mrpackName.length > 0

    // Tab 2: launcher khác
    property bool scanning: false
    property var  detectedInstances: []  // [{source, label, mcVersion, loader}]

    // Tab 3: mã phòng
    property bool roomConnecting: false
    property bool roomConnected: false
    property string roomHost: ""
    property string roomInstanceLabel: ""
    property int    roomNeedCount: 0
    property int    roomTotalMods: 0
    property string roomSizeMB: ""

    function openDialog() {
        dialog.tabIndex = 0;
        dialog.errorText = "";
        dialog.importing = false;
        dialog.progress = 0; dialog.progressCurrent = 0; dialog.progressTotal = 0;
        dialog.mrpackPath = ""; dialog.mrpackName = ""; dialog.mrpackMcVersion = "";
        dialog.mrpackLoader = ""; dialog.mrpackFileCount = 0;
        dialog.scanning = false; dialog.detectedInstances = [];
        dialog.roomConnecting = false; dialog.roomConnected = false;
        dialog.roomHost = ""; dialog.roomInstanceLabel = "";
        dialog.roomNeedCount = 0; dialog.roomTotalMods = 0; dialog.roomSizeMB = "";
        instanceNameField.text = "";
        roomNameField.text = "";
        dialog.visible = true;
        notifier.playUi("open");
    }
    function close() {
        if (dialog.importing) return;
        notifier.playUi("back");
        dialog.visible = false;
    }

    // ── ImportBridge signal handlers ──────────────────────────────────
    Connections {
        target: typeof importBridge !== "undefined" ? importBridge : null
        function onScanDone(instances) {
            dialog.scanning = false;
            dialog.detectedInstances = instances;
        }
        function onMrpackParsed(info) {
            dialog.mrpackName = info.name || "";
            dialog.mrpackMcVersion = info.mcVersion || "";
            dialog.mrpackLoader = info.loader || "";
            dialog.mrpackFileCount = info.fileCount || 0;
            instanceNameField.text = dialog.mrpackName;
        }
        function onImportProgress(current, total) {
            dialog.progressCurrent = current;
            dialog.progressTotal = total;
            dialog.progress = total > 0 ? current / total : 0;
        }
        function onImportDone() {
            dialog.importing = false;
            dialog.visible = false;
        }
        function onImportError(message) {
            dialog.importing = false;
            dialog.errorText = message;
        }
        function onRoomConnected(info) {
            dialog.roomConnecting = false;
            dialog.roomConnected = true;
            dialog.roomHost = info.host || "";
            dialog.roomInstanceLabel = info.instanceLabel || "";
            dialog.roomNeedCount = info.needCount || 0;
            dialog.roomTotalMods = info.totalMods || 0;
            dialog.roomSizeMB = info.sizeMB || "";
            roomNameField.text = dialog.roomInstanceLabel;
        }
    }

    // ── Lớp tối phía sau; bấm ngoài đóng ────────────────────────────
    MouseArea {
        anchors.fill: parent
        onClicked: dialog.close()
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }

    Rectangle {
        id: box
        anchors.centerIn: parent
        width: 520
        height: Math.min(parent.height - 40, 560)
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        scale: dialog.visible ? 1 : 0.96
        Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent }  // nuốt click

        Column {
            id: mainColumn
            anchors { fill: parent; margins: 24 }
            spacing: 16

            // ── Header ───────────────────────────────────────────────
            Row {
                width: parent.width
                Text {
                    text: "Nhập bản chơi"
                    color: Theme.text; font.pixelSize: 18; font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
                Item { width: parent.width - 120; height: 1 }
                Text {
                    text: "✕"
                    color: closeHover.hovered ? Theme.text : Theme.textMuted
                    font.pixelSize: 16
                    anchors.verticalCenter: parent.verticalCenter
                    HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: dialog.close() }
                }
            }

            // ── Tab bar ──────────────────────────────────────────────
            TabBar {
                id: tabs
                width: parent.width
                tabs: ["📦 File .mrpack", "🔍 Launcher khác", "🔗 Mã phòng"]
                currentIndex: dialog.tabIndex
                onCurrentIndexChanged: {
                    dialog.tabIndex = currentIndex;
                    dialog.errorText = "";
                    // Tự động scan khi mở Tab 2 lần đầu
                    if (currentIndex === 1 && dialog.detectedInstances.length === 0 && !dialog.scanning) {
                        dialog.scanning = true;
                        if (typeof importBridge !== "undefined") importBridge.scanLaunchers();
                    }
                }
            }

            // ── Error banner ─────────────────────────────────────────
            Rectangle {
                width: parent.width
                height: dialog.errorText.length > 0 ? errorLabel.implicitHeight + 20 : 0
                radius: Theme.radiusSmall
                color: "#331a0a0a"
                border.color: Theme.danger
                border.width: dialog.errorText.length > 0 ? 1 : 0
                clip: true
                visible: dialog.errorText.length > 0
                Behavior on height { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }

                Text {
                    id: errorLabel
                    anchors { fill: parent; margins: 10 }
                    text: dialog.errorText
                    color: Theme.danger
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }

            // ── Tab content ──────────────────────────────────────────
            Item {
                width: parent.width
                height: mainColumn.height - y

                // ═══════════ TAB 1: File .mrpack ═══════════
                Column {
                    id: tab1
                    visible: dialog.tabIndex === 0
                    width: parent.width
                    spacing: 14

                    Text {
                        text: "Chọn file Modrinth (.mrpack)"
                        color: Theme.textMuted; font.pixelSize: 12
                    }

                    ActionButton {
                        width: parent.width
                        primary: false
                        label: dialog.mrpackPath ? "📄 " + dialog.mrpackPath.split("/").pop() : "Chọn file..."
                        onClicked: mrpackPicker.open()
                    }

                    // Thông tin sau khi chọn file
                    Column {
                        visible: dialog.mrpackReady
                        width: parent.width
                        spacing: 6

                        Rectangle {
                            width: parent.width; height: 1
                            color: Theme.border
                        }

                        Row {
                            spacing: 6
                            Text { text: "Tên:"; color: Theme.textMuted; font.pixelSize: 12 }
                            Text { text: dialog.mrpackName; color: Theme.text; font.pixelSize: 12; font.bold: true }
                        }
                        Row {
                            spacing: 12
                            Row {
                                spacing: 4
                                Text { text: "MC:"; color: Theme.textMuted; font.pixelSize: 12 }
                                Text { text: dialog.mrpackMcVersion; color: Theme.accent; font.pixelSize: 12 }
                            }
                            Row {
                                spacing: 4
                                Text { text: "Loader:"; color: Theme.textMuted; font.pixelSize: 12 }
                                Text { text: dialog.mrpackLoader; color: Theme.accent; font.pixelSize: 12 }
                            }
                        }
                        Row {
                            spacing: 4
                            Text { text: "Mods:"; color: Theme.textMuted; font.pixelSize: 12 }
                            Text { text: dialog.mrpackFileCount + " files"; color: Theme.text; font.pixelSize: 12 }
                        }

                        Item { width: 1; height: 4 }

                        Column {
                            spacing: 5; width: parent.width
                            Text { text: "TÊN BẢN CHƠI"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                            TextField {
                                id: instanceNameField; width: parent.width
                                placeholder: dialog.mrpackName || "Tên bản chơi"
                            }
                        }
                    }

                    Item { width: 1; height: 4 }

                    // Progress bar
                    Column {
                        visible: dialog.importing && dialog.tabIndex === 0
                        width: parent.width
                        spacing: 6

                        Row {
                            width: parent.width
                            Text {
                                text: dialog.progressCurrent + "/" + dialog.progressTotal + " files"
                                color: Theme.textMuted; font.pixelSize: 11
                            }
                            Item { width: parent.width - 140; height: 1 }
                            Text {
                                text: Math.round(dialog.progress * 100) + "%"
                                color: Theme.textMuted; font.pixelSize: 11
                            }
                        }

                        Rectangle {
                            width: parent.width; height: 6; radius: 3
                            color: Theme.surfaceHigh
                            Rectangle {
                                width: parent.width * dialog.progress; height: parent.height; radius: 3
                                color: Theme.accent
                                Behavior on width { NumberAnimation { duration: Theme.quick } }
                            }
                        }
                    }

                    ActionButton {
                        width: parent.width; height: 44
                        label: dialog.importing ? "Đang cài đặt..." : "Cài đặt"
                        clickable: dialog.mrpackReady && !dialog.importing
                        onClicked: {
                            dialog.importing = true;
                            dialog.errorText = "";
                            dialog.progress = 0; dialog.progressCurrent = 0;
                            if (typeof importBridge !== "undefined")
                                importBridge.importMrpack(dialog.mrpackPath,
                                    instanceNameField.text.trim() || dialog.mrpackName);
                        }
                    }
                }

                // ═══════════ TAB 2: Launcher khác ═══════════
                Column {
                    id: tab2
                    visible: dialog.tabIndex === 1
                    width: parent.width
                    spacing: 14

                    Text {
                        text: "Tìm thấy trên máy:"
                        color: Theme.textMuted; font.pixelSize: 12
                    }

                    // Spinner khi đang scan
                    Column {
                        visible: dialog.scanning
                        width: parent.width
                        spacing: 8
                        anchors.horizontalCenter: parent.horizontalCenter

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "⟳"
                            color: Theme.accent; font.pixelSize: 28
                            RotationAnimation on rotation { from: 0; to: 360; duration: 1200; loops: Animation.Infinite }
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Đang quét launcher trên máy..."
                            color: Theme.textMuted; font.pixelSize: 12
                        }
                    }

                    // Danh sách launcher tìm thấy
                    Column {
                        visible: !dialog.scanning && dialog.detectedInstances.length > 0
                        width: parent.width
                        spacing: 6

                        Repeater {
                            model: dialog.detectedInstances
                            Rectangle {
                                width: tab2.width; height: 52
                                radius: Theme.radiusSmall
                                color: launcherHover.hovered ? Theme.surfaceHigh : "transparent"
                                border.color: Theme.border; border.width: 1

                                Row {
                                    anchors { fill: parent; margins: 12 }
                                    spacing: 10

                                    // Icon launcher
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: {
                                            var s = modelData.source || "";
                                            if (s === "prism" || s === "Prism") return "🌐";
                                            if (s === "curseforge" || s === "CurseForge") return "⚡";
                                            if (s === "modrinth" || s === "Modrinth") return "🟢";
                                            if (s === "tlauncher" || s === "TLauncher") return "🎮";
                                            return "☁️";
                                        }
                                        font.pixelSize: 20
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2
                                        Text {
                                            text: "[" + (modelData.source || "?") + "] " + (modelData.label || "Không tên")
                                            color: Theme.text; font.pixelSize: 13; font.bold: true
                                        }
                                        Text {
                                            text: (modelData.mcVersion || "") + "  " + (modelData.loader || "Vanilla")
                                            color: Theme.textMuted; font.pixelSize: 11
                                        }
                                    }

                                    Item { Layout.fillWidth: true; width: 10; height: 1 }
                                }

                                // Nút Nhập ở bên phải
                                ActionButton {
                                    anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                                    primary: false
                                    label: "Nhập"
                                    clickable: !dialog.importing
                                    width: 70; height: 32
                                    onClicked: {
                                        dialog.importing = true;
                                        dialog.errorText = "";
                                        if (typeof importBridge !== "undefined")
                                            importBridge.importFromLauncher(modelData.source, modelData.path || "");
                                    }
                                }

                                HoverHandler { id: launcherHover }
                            }
                        }
                    }

                    // Không tìm thấy launcher nào
                    Column {
                        visible: !dialog.scanning && dialog.detectedInstances.length === 0
                        width: parent.width
                        spacing: 8

                        Text {
                            width: parent.width
                            text: "Không phát hiện launcher nào. Thử dùng tab File .mrpack."
                            color: Theme.textMuted; font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }

                        ActionButton {
                            primary: false
                            label: "Quét lại"
                            onClicked: {
                                dialog.scanning = true;
                                if (typeof importBridge !== "undefined") importBridge.scanLaunchers();
                            }
                        }
                    }

                    // Progress bar cho import từ launcher
                    Column {
                        visible: dialog.importing && dialog.tabIndex === 1
                        width: parent.width
                        spacing: 6

                        Text {
                            text: "Đang nhập..."
                            color: Theme.textMuted; font.pixelSize: 11
                        }
                        Rectangle {
                            width: parent.width; height: 6; radius: 3
                            color: Theme.surfaceHigh
                            Rectangle {
                                width: parent.width * dialog.progress; height: parent.height; radius: 3
                                color: Theme.accent
                                Behavior on width { NumberAnimation { duration: Theme.quick } }
                            }
                        }
                    }
                }

                // ═══════════ TAB 3: Mã phòng ═══════════
                Column {
                    id: tab3
                    visible: dialog.tabIndex === 2
                    width: parent.width
                    spacing: 14

                    Text {
                        text: "Đồng bộ từ phòng"
                        color: Theme.textMuted; font.pixelSize: 12
                    }

                    Column {
                        visible: !dialog.roomConnected
                        width: parent.width
                        spacing: 14

                        Column {
                            spacing: 5; width: parent.width
                            Text { text: "MÃ PHÒNG"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                            RoomCodeInput {
                                id: roomCode
                                onSubmitted: connectBtn.clicked()
                            }
                        }

                        ActionButton {
                            id: connectBtn
                            width: parent.width; height: 40
                            primary: false
                            label: dialog.roomConnecting ? "Đang kết nối..." : "Kết nối"
                            clickable: roomCode.complete && !dialog.roomConnecting
                            onClicked: {
                                dialog.roomConnecting = true;
                                dialog.errorText = "";
                                if (typeof importBridge !== "undefined")
                                    importBridge.connectRoom(roomCode.code);
                            }
                        }

                        // Spinner khi đang kết nối
                        Row {
                            visible: dialog.roomConnecting
                            anchors.horizontalCenter: parent.horizontalCenter
                            spacing: 8
                            Text {
                                text: "⟳"
                                color: Theme.accent; font.pixelSize: 20
                                RotationAnimation on rotation { from: 0; to: 360; duration: 1200; loops: Animation.Infinite }
                            }
                            Text {
                                text: "Đang kết nối tới phòng..."
                                color: Theme.textMuted; font.pixelSize: 12
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }

                    // Thông tin phòng sau khi kết nối thành công
                    Column {
                        visible: dialog.roomConnected
                        width: parent.width
                        spacing: 8

                        Rectangle {
                            width: parent.width; height: 1
                            color: Theme.border
                        }

                        Row {
                            spacing: 6
                            Text { text: "Host:"; color: Theme.textMuted; font.pixelSize: 12 }
                            Text { text: dialog.roomHost; color: Theme.text; font.pixelSize: 12; font.bold: true }
                        }
                        Row {
                            spacing: 6
                            Text { text: "Bản chơi:"; color: Theme.textMuted; font.pixelSize: 12 }
                            Text { text: dialog.roomInstanceLabel; color: Theme.accent; font.pixelSize: 12 }
                        }
                        Row {
                            spacing: 6
                            Text { text: "Cần tải:"; color: Theme.textMuted; font.pixelSize: 12 }
                            Text {
                                text: dialog.roomNeedCount + "/" + dialog.roomTotalMods + " mods"
                                      + (dialog.roomSizeMB ? " (" + dialog.roomSizeMB + ")" : "")
                                color: Theme.text; font.pixelSize: 12
                            }
                        }

                        Item { width: 1; height: 4 }

                        Column {
                            spacing: 5; width: parent.width
                            Text { text: "TÊN BẢN CHƠI"; color: Theme.textMuted; font.pixelSize: 10; font.letterSpacing: 1.2 }
                            TextField {
                                id: roomNameField; width: parent.width
                                placeholder: dialog.roomInstanceLabel || "Tên bản chơi"
                            }
                        }

                        Item { width: 1; height: 4 }

                        // Progress bar cho room sync
                        Column {
                            visible: dialog.importing && dialog.tabIndex === 2
                            width: parent.width
                            spacing: 6

                            Row {
                                width: parent.width
                                Text {
                                    text: dialog.progressCurrent + "/" + dialog.roomNeedCount + " mods"
                                    color: Theme.textMuted; font.pixelSize: 11
                                }
                            }
                            Rectangle {
                                width: parent.width; height: 6; radius: 3
                                color: Theme.surfaceHigh
                                Rectangle {
                                    width: parent.width * dialog.progress; height: parent.height; radius: 3
                                    color: Theme.accent
                                    Behavior on width { NumberAnimation { duration: Theme.quick } }
                                }
                            }
                        }

                        ActionButton {
                            width: parent.width; height: 44
                            label: dialog.importing ? "Đang đồng bộ..." : "Đồng bộ"
                            clickable: dialog.roomConnected && !dialog.importing
                            onClicked: {
                                dialog.importing = true;
                                dialog.errorText = "";
                                dialog.progress = 0; dialog.progressCurrent = 0;
                                if (typeof importBridge !== "undefined")
                                    importBridge.syncRoom(roomCode.code,
                                        roomNameField.text.trim() || dialog.roomInstanceLabel);
                            }
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: mrpackPicker
        title: "Chọn file Modrinth Modpack"
        nameFilters: ["Modrinth Modpack (*.mrpack)", "Mọi file (*)"]
        onAccepted: {
            var path = selectedFile.toString();
            dialog.mrpackPath = path;
            dialog.errorText = "";
            // Nhờ bridge phân tích file
            if (typeof importBridge !== "undefined") importBridge.parseMrpack(path);
        }
    }
}
