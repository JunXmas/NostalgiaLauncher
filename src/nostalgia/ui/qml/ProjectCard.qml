import QtQuick

/* Thẻ lưới của thư viện: icon phóng to làm nền mờ bên phải, tên, mô tả hai dòng, nhãn loader,
   số tải / theo dõi, và nút cài. */
Rectangle {
    id: root
    property var project: ({})
    property bool installable: true
    signal installRequested(string projectId)
    signal modpackRequested(string projectId, string title)
    readonly property bool isModpack: (project.contentKind || "") === "modpack"

    height: 118
    radius: Theme.radiusSmall
    color: hover.hovered ? Theme.surfaceHigh : Theme.surface
    border.color: hover.hovered ? Theme.accent : Theme.border
    border.width: 1
    clip: true
    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on border.color { ColorAnimation { duration: Theme.quick } }
    scale: hover.hovered ? 1.01 : 1.0
    Behavior on scale { NumberAnimation { duration: Theme.quick } }

    MicaBackdrop { source: project.iconUrl || "" }

    ProjectIcon {
        id: icon
        width: 56; height: 56
        anchors { left: parent.left; top: parent.top; margins: 14 }
        source: project.iconUrl || ""
        fallbackText: project.title || "?"
    }
    Column {
        anchors { left: icon.right; leftMargin: 14; right: action.left; rightMargin: 12; top: parent.top; topMargin: 14 }
        spacing: 4
        Text {
            width: parent.width
            text: project.title || ""
            color: hover.hovered ? Theme.accent : Theme.text; font.pixelSize: 14; font.bold: true; elide: Text.ElideRight
            Behavior on color { ColorAnimation { duration: Theme.quick } }
        }
        Text {
            width: parent.width
            text: project.description || ""
            color: Theme.textMuted; font.pixelSize: 11
            wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
        }
    }
    Row {
        anchors { left: icon.right; leftMargin: 14; bottom: parent.bottom; bottomMargin: 12 }
        spacing: 6
        Repeater {
            model: (project.loaders || []).slice(0, 3)
            Rectangle {
                width: loaderText.width + 14; height: 18; radius: 5
                color: Theme.accentSoft
                Text { id: loaderText; anchors.centerIn: parent; text: modelData; color: Theme.accent; font.pixelSize: 10 }
            }
        }
    }
    Row {
        anchors { right: parent.right; rightMargin: 14; bottom: parent.bottom; bottomMargin: 14 }
        spacing: 12
        Text { text: "⬇ " + Theme.compact(project.downloads || 0); color: Theme.accent; font.pixelSize: 11 }
        // CurseForge không có "theo dõi": không vẽ số 0 giả.
        Text {
            visible: (project.source || "modrinth") === "modrinth"
            text: "♥ " + Theme.compact(project.follows || 0); color: Theme.textMuted; font.pixelSize: 11
        }
    }
    ActionButton {
        id: action
        anchors { right: parent.right; top: parent.top; margins: 14 }
        width: root.isModpack ? 120 : 84; height: 30
        label: root.isModpack ? (project.installing ? "Đang cài..." : "Tạo bản chơi")
             : project.installed ? "Đã cài" : project.installing ? "Đang cài..." : "Cài"
        primary: !project.installed
        clickable: !project.installing && (root.isModpack || (root.installable && !project.installed))
        onClicked: root.isModpack ? root.modpackRequested(project.projectId, project.title)
                                  : root.installRequested(project.projectId)
    }
    HoverHandler { id: hover }
}
