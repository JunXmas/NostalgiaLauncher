import QtQuick

/* Một file đã cài: tên, tên file, dung lượng; công tắc bật/tắt (chỉ mod) và nút gỡ. */
Rectangle {
    id: root
    property var installedContent: ({})
    property bool toggleable: true
    signal toggled(string fileName, bool enabled)
    signal removeRequested(string fileName)

    height: 60
    radius: Theme.radiusSmall
    color: hover.hovered ? Theme.surfaceHigh : Theme.surface
    border.color: Theme.border
    border.width: 1
    opacity: installedContent.enabled ? 1 : 0.55
    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on opacity { NumberAnimation { duration: Theme.quick } }

    ProjectIcon {
        id: icon
        width: 36; height: 36
        anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
        fallbackText: installedContent.label || "?"
    }
    Column {
        anchors { left: icon.right; leftMargin: 12; right: controls.left; rightMargin: 12
                  verticalCenter: parent.verticalCenter }
        spacing: 3
        Text {
            width: parent.width
            text: installedContent.label || ""
            color: Theme.text; font.pixelSize: 13; font.bold: true; elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: (installedContent.fileName || "")
                  + (installedContent.versionNumber ? "  ·  v" + installedContent.versionNumber : "")
                  + "  ·  " + Theme.fileSize(installedContent.fileSize || 0)
            color: Theme.textMuted; font.pixelSize: 10; font.family: "monospace"; elide: Text.ElideRight
        }
    }
    Row {
        id: controls
        anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
        spacing: 14
        Toggle {
            visible: root.toggleable
            anchors.verticalCenter: parent.verticalCenter
            checked: !!installedContent.enabled
            onToggled: function (enabled) { root.toggled(installedContent.fileName, enabled); }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "🗑"; font.pixelSize: 14
            color: trashHover.hovered ? Theme.danger : Theme.textMuted
            opacity: hover.hovered ? 1 : 0.35
            Behavior on opacity { NumberAnimation { duration: Theme.quick } }
            HoverHandler { id: trashHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.removeRequested(installedContent.fileName) }
        }
    }
    HoverHandler { id: hover }
}
