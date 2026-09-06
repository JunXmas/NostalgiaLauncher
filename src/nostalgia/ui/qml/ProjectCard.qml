import QtQuick

/* Thẻ lưới của thư viện: icon phóng to làm nền mờ bên phải, tên, mô tả hai dòng, nhãn loader,
   số tải / theo dõi, và nút cài. */
Rectangle {
    id: root
    property var project: ({})
    property bool installable: true
    signal installRequested(string projectId)

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

    // Nền kiểu mica: chính icon mod, tải ở cỡ 10×10 rồi phóng to có nội suy — ra một mảng màu
    // mờ mà không cần shader (MultiEffect blur không vẽ được trên GL phần mềm, đã thử).
    Image {
        source: project.iconUrl || ""
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: parent.width * 0.7
        sourceSize: Qt.size(10, 10)
        smooth: true
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        opacity: status === Image.Ready ? 0.8 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Theme.surface }
            GradientStop { position: 0.35; color: "#e6111713" }
            GradientStop { position: 0.7; color: "#80111713" }
            GradientStop { position: 1.0; color: "#26111713" }
        }
    }

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
        Text { text: "♥ " + Theme.compact(project.follows || 0); color: Theme.textMuted; font.pixelSize: 11 }
    }
    ActionButton {
        id: action
        anchors { right: parent.right; top: parent.top; margins: 14 }
        width: 84; height: 30
        label: project.installed ? "Đã cài" : project.installing ? "Đang cài..." : "Cài"
        primary: !project.installed
        clickable: root.installable && !project.installed && !project.installing
        onClicked: root.installRequested(project.projectId)
    }
    HoverHandler { id: hover }
}
