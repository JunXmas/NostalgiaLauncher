import QtQuick

/* Một kết quả tìm kiếm: icon, tên, tác giả, mô tả, số tải, và nút cài ba trạng thái. */
Rectangle {
    id: root
    property var project: ({})
    property bool installable: true
    signal installRequested(string projectId, string title, bool alreadyInstalled)

    height: 74
    radius: Theme.radiusSmall
    color: hover.hovered ? Theme.surfaceHigh : Theme.surface
    border.color: hover.hovered ? Theme.accent : Theme.border
    border.width: 1
    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }

    ProjectIcon {
        id: icon
        anchors { left: parent.left; verticalCenter: parent.verticalCenter; leftMargin: 14 }
        source: project.iconUrl || ""
        fallbackText: project.title || "?"
    }

    Column {
        anchors { left: icon.right; leftMargin: 14; right: stats.left; rightMargin: 14
                  verticalCenter: parent.verticalCenter }
        spacing: 3
        Row {
            spacing: 8
            Text { text: project.title || ""; color: Theme.text; font.pixelSize: 13; font.bold: true }
            Text {
                visible: !!project.author
                text: "· " + (project.author || "")
                color: Theme.textMuted; font.pixelSize: 11
                anchors.baseline: parent.children[0].baseline
            }
        }
        Text {
            width: parent.width
            text: project.description || ""
            color: Theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight
        }
        Row {
            spacing: 6
            Repeater {
                model: project.loaders || []
                Rectangle {
                    width: loaderText.width + 12; height: 16; radius: 4
                    color: Theme.accentSoft
                    Text {
                        id: loaderText
                        anchors.centerIn: parent
                        text: modelData; color: Theme.accent; font.pixelSize: 9
                    }
                }
            }
        }
    }

    Column {
        id: stats
        anchors { right: action.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
        spacing: 3
        Text {
            anchors.right: parent.right
            text: "⬇ " + Theme.compact(project.downloads || 0)
            color: Theme.accent; font.pixelSize: 11
        }
        Text {
            anchors.right: parent.right
            text: "♥ " + Theme.compact(project.follows || 0)
            color: Theme.textMuted; font.pixelSize: 11
        }
    }

    ActionButton {
        id: action
        anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
        width: 92
        label: project.installed ? "Đã cài" : project.installing ? "Đang cài..." : "Cài"
        // Đã cài thì nút xám nhưng VẪN bấm được: trang sẽ hỏi lại trước khi cài đè.
        primary: !project.installed
        clickable: root.installable && !project.installing
        onClicked: root.installRequested(project.projectId, project.title, project.installed)
    }

    HoverHandler { id: hover }
}
