import QtQuick
import QtQuick.Controls

Flickable {
    id: root
    clip: true
    contentWidth: width
    flickableDirection: Flickable.VerticalFlick
    boundsBehavior: Flickable.StopAtBounds
    maximumFlickVelocity: 2200
    flickDeceleration: 1800
    activeFocusOnTab: true
    readonly property real maxY: Math.max(0, contentHeight - height)
    acceptedButtons: Qt.LeftButton
    readonly property real destination: controller.destination
    readonly property real damping: controller.damping
    readonly property bool settling: controller.settling
    function clamp(y) { return controller.clamp(y); }
    function stopMotion() { controller.stopMotion(); }
    function scrollBy(delta, immediate) { controller.scrollBy(delta, immediate); }
    InertialMotion { id: controller; target: root }
    Keys.onDownPressed: scrollBy(64, false)
    Keys.onUpPressed: scrollBy(-64, false)
    Keys.onPressed: function (event) {
        if (event.key === Qt.Key_PageDown)
            scrollBy(height * 0.85, false);
        else if (event.key === Qt.Key_PageUp)
            scrollBy(-height * 0.85, false);
        else if (event.key === Qt.Key_Home)
            scrollBy(-maxY, false);
        else if (event.key === Qt.Key_End)
            scrollBy(maxY, false);
        else {
            event.accepted = false;
            return;
        }
        event.accepted = true;
    }
    ScrollBar.vertical: ScrollBar {
        id: bar
        width: 5
        policy: ScrollBar.AsNeeded
        visible: root.maxY > 1
        opacity: bar.pressed || bar.hovered || root.moving || root.settling ? 1 : 0.35
        onPressedChanged: if (pressed)
            root.stopMotion()
        background: Item {}
        contentItem: Rectangle {
            radius: 3
            color: bar.pressed ? GlassTheme.accent : GlassTheme.alpha(GlassTheme.muted, 0.55)
        }
    }
}
