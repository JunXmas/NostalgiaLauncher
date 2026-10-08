import QtQuick
import "preview" as Preview

Preview.Glass {
    id: root
    padding: 0
    frosted: Theme.modern
    backdrop: Theme.modern ? Theme.modalBackdrop : null
    blurOpacity: 0.92
    blurRadius: 64
    radius: Theme.radius
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        visible: Theme.modern && !root.shaderAvailable
        color: Theme.surface
        border.color: Theme.border
    }
    onVisibleChanged: if (visible) entrance.restart()
    ParallelAnimation {
        id: entrance
        NumberAnimation { target: root; property: "opacity"; from: Theme.reducedMotion ? 1 : 0; to: 1; duration: Theme.normal; easing.type: Easing.OutCubic }
    }
}
