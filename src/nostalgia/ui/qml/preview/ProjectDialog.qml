import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
        }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: GlassTheme.quick } }
    objectName: "projectDialog"
    parent: Controls.Overlay.overlay
    width: Math.min(760, parent ? parent.width - 48 : 760)
    height: Math.min(620, parent ? parent.height - 48 : 620)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24
    modal: true
    dim: true
    focus: true
    closePolicy: projectBridge.installing ? Controls.Popup.NoAutoClose : Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutside
    property var details: projectBridge.details
    property string success: ""
    property string openedProject: ""
    property Item backdrop: null
    signal createRequested(string gameVersion, string loaderKind)
    background: Glass {
        id: popupMica
        objectName: "projectMica"
        padding: 0
        radius: 22
        color: "transparent"
        backdrop: root.backdrop
        backdropRect: {
            if (!root.backdrop || !root.parent)
                return Qt.rect(0, 0, 1, 1);
            // X/Y của Popup đổi khi mở và resize; mapToItem không tự theo dõi tổ tiên.
            var origin = root.parent.mapToItem(root.backdrop, root.x, root.y);
            return Qt.rect(origin.x, origin.y, root.width, root.height);
        }
        frosted: root.opened
        blurOpacity: 0.95
        blurRadius: 64
        finishOpacity: 0.45
        Rectangle {
            anchors.fill: parent
            radius: popupMica.radius
            color: GlassTheme.alpha(GlassTheme.surface, popupMica.shaderAvailable ? 0.45 : 0.94)
            border.color: GlassTheme.alpha(GlassTheme.text, 0.14)
        }
    }
    Controls.Overlay.modal: Rectangle {
        color: "#aa080b12"
    }
    Connections {
        target: projectBridge
        function onOpened() {
            root.success = "";
            if (root.openedProject !== root.details.projectId) {
                root.openedProject = root.details.projectId;
                nameField.text = "";
                picker.reset();
                aboutScroll.contentY = 0;
            }
            root.open();
        }
        function onInstalled(title) {
            root.success = "Đã cài " + title + " thành công.";
        }
        function onInstallingChanged() {
            if (projectBridge.installing) {
                root.success = "";
                bridge.clearProgress();
            }
        }
    }
    contentItem: Item {
        id: dialogContent
        Item {
            id: header
            width: parent.width
            height: 66
            Legacy.ProjectIcon {
                id: avatar
                width: 58
                height: 58
                source: root.details.iconUrl || ""
                fallbackText: root.details.title || "?"
            }
            Column {
                anchors.left: avatar.right
                anchors.leftMargin: 16
                anchors.right: closeButton.left
                anchors.rightMargin: 12
                spacing: 7
                Text {
                    width: parent.width
                    text: root.details.title || ""
                    color: GlassTheme.text
                    font.family: GlassTheme.displayFont
                    font.pixelSize: GlassTheme.fontDialog
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Text {
                    width: parent.width
                    text: (root.details.author ? root.details.author + "  ·  " : "") + (root.details.source === "curseforge" ? "CurseForge" : "Modrinth")
                    color: GlassTheme.muted
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontLabel
                    elide: Text.ElideRight
                }
            }
            Button {
                id: closeButton
                objectName: "projectClose"
                anchors.right: parent.right
                width: 38
                height: 38
                label: "×"
                quiet: true
                clickable: !projectBridge.installing
                Accessible.name: "Đóng giới thiệu dự án"
                onClicked: root.close()
            }
        }
        Item {
            id: footer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 46 * GlassTheme.scale + (projectBridge.installing ? 36 : 0)
            Column {
                width: parent.width
                spacing: 8
                visible: projectBridge.installing
                Text {
                    width: parent.width
                    text: bridge.progressText || projectBridge.activity
                    color: GlassTheme.muted
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontLabel
                    elide: Text.ElideRight
                }
                Controls.ProgressBar {
                    width: parent.width
                    height: 4
                    value: bridge.progressFraction
                    indeterminate: value <= 0 || value >= 1
                }
            }
            Button {
                objectName: "projectWebsite"
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                label: "Trang dự án  ↗"
                quiet: true
                visible: !!root.details.websiteUrl
                onClicked: Qt.openUrlExternally(root.details.websiteUrl)
            }
            Button {
                objectName: "projectInstall"
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                label: projectBridge.installing ? "Đang cài…" : picker.isPack ? "Tạo bản chơi" : "Cài phiên bản đã chọn"
                primary: true
                clickable: !root.details.loading && !projectBridge.installing && !contentBridge.busy && picker.canInstall && !root.success
                onClicked: projectBridge.installVersion(picker.versionId, picker.gameVersion, picker.instanceId, nameField.text)
            }
        }
        InertialScroll {
            id: bodyScroll
            objectName: "projectBodyScroll"
            anchors.top: header.bottom
            anchors.topMargin: 14
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: footer.top
            anchors.bottomMargin: 16
            contentHeight: body.height
            Column {
                id: body
                width: parent.width - 10
                spacing: 16
                Text {
                    text: "Giới thiệu"
                    color: GlassTheme.text
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontSubheading
                    font.weight: Font.DemiBold
                }
                Rectangle {
                    width: parent.width
                    height: Math.min(172, Math.max(64, aboutText.implicitHeight + 24))
                    radius: 12
                    color: GlassTheme.alpha(GlassTheme.background, 0.60)
                    border.color: GlassTheme.stroke
                    InertialScroll {
                        id: aboutScroll
                        anchors.fill: parent
                        anchors.margins: 12
                        contentHeight: aboutText.height
                        TextEdit {
                            id: aboutText
                            objectName: "projectAbout"
                            width: parent.width - 10
                            text: root.details.about || root.details.description || "Chưa có giới thiệu cho dự án này."
                            textFormat: TextEdit.PlainText
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.Wrap
                            color: GlassTheme.text
                            font.family: GlassTheme.font
                            font.pixelSize: GlassTheme.fontBody
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: !!root.details.notice
                    text: root.details.notice || ""
                    color: GlassTheme.muted
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontLabel
                    wrapMode: Text.Wrap
                }
                Text {
                    objectName: "projectLoading"
                    visible: root.details.loading === true
                    text: "Đang lấy giới thiệu và các phiên bản…"
                    color: GlassTheme.muted
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontBody
                }
                Text {
                    objectName: "projectError"
                    width: parent.width
                    visible: !!root.details.error && !projectBridge.installing && !root.success
                    text: root.details.error || ""
                    color: GlassTheme.danger
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontBody
                    wrapMode: Text.Wrap
                }
                Button {
                    objectName: "projectRetry"
                    visible: !!root.details.error && !root.details.versions.length
                    label: "Thử lại"
                    quiet: true
                    onClicked: projectBridge.reload()
                }
                ProjectVersionPicker {
                    id: picker
                    // The menu lives in Overlay, outside this popup's visual item.
                    // Capture the dialog beneath it without capturing the menu itself.
                    menuBackdrop: dialogContent.parent
                    width: parent.width
                    details: root.details
                    visible: !root.details.loading && root.details.versions.length > 0
                    onCreateRequested: function (gameVersion, loaderKind) {
                        root.createRequested(gameVersion, loaderKind);
                    }
                }
                Input {
                    id: nameField
                    objectName: "projectPackName"
                    width: parent.width
                    visible: picker.visible && picker.isPack
                    placeholder: "Tên bản chơi mới (mặc định: " + (root.details.title || "") + ")"
                    enabled: !projectBridge.installing
                }
                Text {
                    objectName: "projectSuccess"
                    width: parent.width
                    visible: !!root.success
                    text: root.success
                    color: GlassTheme.brand
                    font.family: GlassTheme.font
                    font.pixelSize: GlassTheme.fontBody
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
