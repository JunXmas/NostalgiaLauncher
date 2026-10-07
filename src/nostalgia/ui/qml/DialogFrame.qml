import QtQuick
import "preview" as Preview

Preview.Glass {
    id: root
    padding: 0
    frosted: Theme.modern
    radius: Theme.radius
    onVisibleChanged: if (visible) entrance.restart()
    ParallelAnimation {
        id: entrance
        NumberAnimation { target: root; property: "opacity"; from: Theme.reducedMotion ? 1 : 0; to: 1; duration: Theme.normal; easing.type: Easing.OutCubic }
    }
}
