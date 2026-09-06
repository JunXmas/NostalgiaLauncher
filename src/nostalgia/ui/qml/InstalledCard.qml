import QtQuick

/* Thẻ lưới của tab "Đã cài": cùng bố cục và nền mica như thẻ thư viện; thêm công tắc bật/tắt
   (chỉ mod) và nút gỡ hai bước. File chép tay không có icon thì nền là chữ cái đầu. */
Rectangle {
    id: root
    property var installedContent: ({})
    property bool toggleable: true
    property bool confirmingRemove: false
    signal toggled(string fileName, bool enabled)
    signal removeRequested(string fileName)
    signal updateRequested(string fileName)
    readonly property bool hasUpdate: !!(installedContent.latestVersion)

    height: 118
    radius: Theme.radiusSmall
    color: hover.hovered ? Theme.surfaceHigh : Theme.surface
    border.color: hover.hovered ? Theme.accent : Theme.border
    border.width: 1
    clip: true
    opacity: installedContent.enabled ? 1 : 0.55
    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }
    Behavior on opacity { NumberAnimation { duration: Theme.quick } }

    MicaBackdrop { source: installedContent.iconUrl || "" }

    ProjectIcon {
        id: icon
        width: 56; height: 56
        anchors { left: parent.left; top: parent.top; margins: 14 }
        source: installedContent.iconUrl || ""
        fallbackText: installedContent.label || "?"
    }
    Column {
        anchors { left: icon.right; leftMargin: 14; right: controls.left; rightMargin: 12; top: parent.top; topMargin: 14 }
        spacing: 4
        Text {
            width: parent.width
            text: installedContent.label || ""
            color: hover.hovered ? Theme.accent : Theme.text; font.pixelSize: 14; font.bold: true; elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: installedContent.fileName || ""
            color: Theme.textMuted; font.pixelSize: 10; font.family: "monospace"; elide: Text.ElideRight
        }
    }
    Row {
        anchors { left: icon.right; leftMargin: 14; bottom: parent.bottom; bottomMargin: 12 }
        spacing: 6
        Rectangle {
            visible: !!installedContent.versionNumber
            width: versionText.width + 14; height: 18; radius: 5; color: Theme.accentSoft
            Text { id: versionText; anchors.centerIn: parent; text: "v" + installedContent.versionNumber; color: Theme.accent; font.pixelSize: 10 }
        }
        Rectangle {
            width: sizeText.width + 14; height: 18; radius: 5; color: Theme.surfaceHigh; border.color: Theme.border
            Text { id: sizeText; anchors.centerIn: parent; text: Theme.fileSize(installedContent.fileSize || 0); color: Theme.textMuted; font.pixelSize: 10 }
        }
        Rectangle {
            visible: !installedContent.enabled
            width: offText.width + 14; height: 18; radius: 5; color: Theme.surfaceHigh; border.color: Theme.border
            Text { id: offText; anchors.centerIn: parent; text: "đã tắt"; color: Theme.textMuted; font.pixelSize: 10 }
        }
        Rectangle {
            visible: root.hasUpdate
            width: updateText.width + 14; height: 18; radius: 5; color: Theme.accentDeep
            Text { id: updateText; anchors.centerIn: parent; text: "mới: " + (installedContent.latestVersion || ""); color: "white"; font.pixelSize: 10 }
            HoverHandler { cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.updateRequested(installedContent.fileName) }
        }
    }
    Column {
        id: controls
        anchors { right: parent.right; top: parent.top; margins: 14 }
        spacing: 10
        Toggle {
            visible: root.toggleable
            anchors.right: parent.right
            checked: !!installedContent.enabled
            onToggled: function (enabled) { root.toggled(installedContent.fileName, enabled); }
        }
        Rectangle {
            anchors.right: parent.right
            width: removeText.width + 16; height: 24; radius: 6
            color: root.confirmingRemove ? Theme.danger : "transparent"
            Text {
                id: removeText
                anchors.centerIn: parent
                text: root.confirmingRemove ? "Gỡ?" : "🗑"; font.pixelSize: 12; font.bold: root.confirmingRemove
                color: root.confirmingRemove ? "white" : (trashHover.hovered ? Theme.danger : Theme.textMuted)
            }
            HoverHandler { id: trashHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: {
                    if (root.confirmingRemove) { root.confirmingRemove = false; root.removeRequested(installedContent.fileName); }
                    else root.confirmingRemove = true;
                }
            }
        }
    }
    HoverHandler { id: hover; onHoveredChanged: if (!hovered) root.confirmingRemove = false }
}
