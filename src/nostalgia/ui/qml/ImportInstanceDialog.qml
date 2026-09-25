import QtQuick
import QtQuick.Dialogs

/* Hộp thoại nhập bản chơi — hai tab: file .mrpack và launcher khác.
   Mở từ nút "Nhập bản chơi" trên trang Bản chơi. */
Item {
    id: dialog
    visible: false
    z: 100

    property int currentTab: 0

    function openDialog() {
        dialog.currentTab = 0;
        dialog.visible = true;
        notifier.playUi("open");
        importBridge.scanLaunchers();
    }
    function close() {
        notifier.playUi("back");
        dialog.visible = false;
    }

    Connections {
        target: importBridge
        function onImportDone(instanceId) { dialog.close(); }
        // Lỗi đã lên dải báo ở Main.qml (failed + importError); hộp thoại cứ mở để chọn lại.
        function onImportError(message) {}
    }

    // Màn tối phía sau
    MouseArea {
        anchors.fill: parent
        onClicked: if (!importBridge.busy) dialog.close()
        Rectangle { anchors.fill: parent; color: "#b3000000" }
    }

    Rectangle {
        id: box
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 760)
        height: Math.min(parent.height - 20, 560)
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        scale: dialog.visible ? 1 : 0.96
        Behavior on scale { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent }

        // Header
        Item {
            id: dialogHeader
            anchors { top: parent.top; left: parent.left; right: parent.right; margins: 24 }
            height: 40

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Nhập bản chơi"
                color: Theme.text; font.pixelSize: Theme.fontTitle; font.bold: true
            }
            Text {
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                text: "✕"; color: closeHover.hovered ? Theme.text : Theme.textMuted; font.pixelSize: Theme.fontHeading
                HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: if (!importBridge.busy) dialog.close() }
            }
        }

        // Tab bar
        Row {
            id: tabBar
            anchors { top: dialogHeader.bottom; left: parent.left; right: parent.right; margins: 24; topMargin: 8 }
            spacing: 0
            Repeater {
                model: [
                    { label: "Từ file .mrpack", idx: 0 },
                    { label: "Từ launcher khác", idx: 1 }
                ]
                Rectangle {
                    readonly property bool active: dialog.currentTab === modelData.idx
                    width: (tabBar.width) / 2; height: 36
                    color: active ? Theme.accentSoft : "transparent"
                    border.color: active ? Theme.accent : Theme.border
                    border.width: active ? 1 : 0
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; color: active ? Theme.accent : "transparent" }
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: active ? Theme.accent : Theme.text; font.pixelSize: Theme.fontBody; font.bold: active
                    }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: { dialog.currentTab = modelData.idx; notifier.playUi("nav"); } }
                }
            }
        }

        Rectangle {
            anchors { top: tabBar.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.border
        }

        // Tab content
        Item {
            anchors { top: tabBar.bottom; topMargin: 16; left: parent.left; right: parent.right; bottom: parent.bottom; margins: 24 }

            // Tab 0: Từ file .mrpack
            Column {
                visible: dialog.currentTab === 0
                anchors { left: parent.left; right: parent.right }
                spacing: 16

                Text { text: "Chọn file modpack (.mrpack hoặc .zip) từ máy tính"; color: Theme.textMuted; font.pixelSize: Theme.fontBody }

                ActionButton {
                    width: 200; height: 40
                    label: "Chọn file..."
                    clickable: !importBridge.busy
                    onClicked: mrpackPicker.open()
                }

                Text {
                    visible: importBridge.busy
                    text: bridge.progressText
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
            }

            // Tab 1: Từ launcher khác
            Column {
                visible: dialog.currentTab === 1
                anchors.fill: parent
                spacing: 12

                Text {
                    text: importBridge.busy && importBridge.activity === "Đang quét launcher trên máy..."
                          ? "Đang quét..."
                          : importBridge.scanResults.length === 0 ? "Không tìm thấy launcher nào trên máy."
                          : importBridge.scanResults.length + " bản chơi tìm thấy"
                    color: Theme.textMuted; font.pixelSize: Theme.fontBody
                }
                ActionButton {
                    primary: false; label: "Quét lại"
                    clickable: !importBridge.busy
                    onClicked: importBridge.scanLaunchers()
                }

                ListView {
                    anchors { left: parent.left; right: parent.right }
                    height: parent.height - 80
                    clip: true; spacing: 6
                    model: importBridge.scanResults
                    delegate: Rectangle {
                        width: ListView.view.width; height: 52; radius: 0
                        color: launcherHover.hovered ? Theme.surfaceHigh : Theme.surface
                        border.color: Theme.border
                        Column {
                            anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
                            spacing: 2
                            Text { text: modelData.instanceName; color: Theme.text; font.pixelSize: Theme.fontHeading; font.bold: true }
                            Row {
                                spacing: 8
                                Text { text: modelData.launcher; color: Theme.accent; font.pixelSize: Theme.fontLabel }
                                Text { text: modelData.gameVersion || "?"; color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
                                Text { text: modelData.loaderKind !== "vanilla" ? modelData.loaderKind : ""; color: Theme.textMuted; font.pixelSize: Theme.fontLabel }
                            }
                        }
                        ActionButton {
                            anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                            primary: false; label: "Nhập"
                            clickable: !importBridge.busy
                            onClicked: importBridge.importFromLauncher(index, "")
                        }
                        HoverHandler { id: launcherHover }
                    }
                }
            }
        }
    }

    FileDialog {
        id: mrpackPicker
        title: "Chọn modpack"
        nameFilters: ["Modpack (*.mrpack *.zip)", "Mọi file (*)"]
        onAccepted: importBridge.importMrpackFile(selectedFile.toString(), "", "")
    }
}
