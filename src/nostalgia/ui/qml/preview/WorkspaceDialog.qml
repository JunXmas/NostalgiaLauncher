import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy

Controls.Popup {
    id: root
    default property alias body: bodyArea.data
    property alias footer: footerArea.data
    property string title: ""
    property string description: ""
    property bool busy: false
    property int preferredWidth: 800
    property int preferredHeight: 670
    readonly property real bodyWidth: bodyArea.width
    readonly property real bodyHeight: bodyArea.height
    parent: Controls.Overlay.overlay
    width: Math.min(preferredWidth, parent ? parent.width - 40 : preferredWidth)
    height: Math.min(preferredHeight, parent ? parent.height - 40 : preferredHeight)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24; modal: true; dim: true; focus: true
    closePolicy: busy ? Controls.Popup.NoAutoClose : Controls.Popup.CloseOnEscape
    Controls.Overlay.modal: Rectangle { color: "#a8080b12" }
    background: PopupGlass {}
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: GlassTheme.normal }
            NumberAnimation { property: "scale"; from: GlassTheme.reducedMotion ? 1 : 0.98; to: 1; duration: GlassTheme.normal; easing.type: Easing.OutCubic }
        }
    }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: GlassTheme.quick } }
    contentItem: Item {
        Column {
            id: heading
            width: parent.width - closeButton.width - 12; spacing: 8
            PaymentText { width: parent.width; text: root.title; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontDialog; font.weight: Font.DemiBold }
            PaymentText { width: parent.width; text: root.description; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
        }
        Button { id: closeButton; anchors.right: parent.right; label: "×"; width: 36; quiet: true; Accessible.name: "Đóng " + root.title; clickable: !root.busy; onClicked: root.close() }
        Item {
            id: bodyArea
            anchors { top: heading.bottom; topMargin: 20; left: parent.left; right: parent.right; bottom: footerArea.top; bottomMargin: 18 }
            clip: true
        }
        Item {
            id: footerArea
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            implicitHeight: childrenRect.height
            height: implicitHeight
        }
    }
}
