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
    property real destination: 0
    property real lastFrame: 0
    readonly property bool settling: motion.running
    function clamp(y) {
        return Math.max(0, Math.min(maxY, y));
    }
    function stopMotion() {
        motion.stop();
        destination = clamp(contentY);
    }
    function scrollBy(delta, precise) {
        cancelFlick();
        destination = clamp((motion.running ? destination : contentY) + delta);
        if (GlassTheme.reducedMotion || precise) {
            motion.stop();
            contentY = destination;
        } else if (Math.abs(destination - contentY) > 0.4) {
            if (!motion.running) {
                lastFrame = Date.now();
                motion.start();
            }
        }
    }
    onDraggingChanged: if (dragging)
        stopMotion()
    onMaxYChanged: {
        destination = clamp(destination);
        if (!dragging && !flicking && contentY > maxY)
            contentY = maxY;
    }
    onContentYChanged: if (!motion.running)
        destination = clamp(contentY)
    Connections {
        target: GlassTheme
        function onReducedMotionChanged() {
            if (GlassTheme.reducedMotion) {
                motion.stop();
                root.contentY = root.destination;
            }
        }
    }
    Timer {
        id: motion
        interval: 16
        repeat: true
        onTriggered: {
            var now = Date.now();
            var dt = Math.min(0.05, Math.max(0.001, (now - root.lastFrame) / 1000));
            root.lastFrame = now;
            // Equivalent to Lenis lerp 0.1 at 60fps; independent of frame rate.
            var ratio = 1 - Math.exp(-6.32 * dt);
            var remaining = root.destination - root.contentY;
            if (Math.abs(remaining) < 0.4) {
                root.contentY = root.destination;
                stop();
            } else
                root.contentY = root.clamp(root.contentY + remaining * ratio);
        }
    }
    WheelHandler {
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function (event) {
            var precise = Math.abs(event.pixelDelta.y) > 0;
            var delta = precise ? -event.pixelDelta.y : -event.angleDelta.y / 120 * 92;
            if (!delta || !root.maxY) {
                event.accepted = false;
                return;
            }
            var origin = motion.running ? root.destination : root.contentY;
            if ((delta < 0 && origin <= 0) || (delta > 0 && origin >= root.maxY)) {
                event.accepted = false;
                return;
            }
            event.accepted = true;
            root.scrollBy(delta, precise);
        }
    }
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
            color: bar.pressed ? GlassTheme.accent : "#557d9190"
        }
    }
}
