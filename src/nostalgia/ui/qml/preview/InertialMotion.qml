import QtQuick
import QtQuick.Window

/* One render-clock controller for both page Flickables and virtualized ListViews.
   Lenis on Skew smooths wheel input, including pixel deltas, with duration 1.5 s.
   Native dragging follows the pointer; release velocity becomes an exponential coast. */
Item {
    id: root
    property Flickable target: null
    readonly property bool renderActive: target && target.visible && target.Window.window && target.Window.window.visible && target.Window.window.visibility !== Window.Minimized
    onRenderActiveChanged: if (!renderActive) stopMotion()
    readonly property real maxY: target ? Math.max(0, target.contentHeight - target.height) : 0
    property real destination: 0
    property real dragSpeed: 0
    property real dragY: 0
    property real dragTime: 0
    readonly property real damping: 10 * Math.LN2 / 1.5
    readonly property bool settling: motion.running
    function clamp(y) { return Math.max(0, Math.min(maxY, y)); }
    function stopMotion() {
        motion.stop();
        if (target) {
            target.cancelFlick();
            destination = clamp(target.contentY);
        }
    }
    function scrollBy(delta, immediate) {
        if (!target || !enabled || !renderActive) return;
        var reversing = motion.running && delta * (destination - target.contentY) < 0;
        var origin = motion.running && !reversing ? destination : target.contentY;
        target.cancelFlick();
        destination = clamp(origin + delta);
        if (GlassTheme.reducedMotion || immediate) {
            motion.stop();
            target.contentY = destination;
        } else if (Math.abs(destination - target.contentY) > 0.4) {
            motion.start();
        }
    }
    function coast(speed) {
        if (!target || !enabled || !renderActive) return;
        target.cancelFlick();
        destination = clamp(target.contentY);
        if (!GlassTheme.reducedMotion && Math.abs(speed) > 40)
            scrollBy(Math.max(-2200, Math.min(2200, speed)) / damping, false);
    }
    function fitBounds() {
        destination = clamp(destination);
        if (target && !target.dragging && target.contentY > maxY)
            target.contentY = maxY;
    }
    onEnabledChanged: if (!enabled) stopMotion()
    Connections {
        target: root.target
        function onDraggingChanged() {
            if (root.target.dragging) {
                root.stopMotion();
                root.dragSpeed = 0;
                root.dragY = root.target.contentY;
                root.dragTime = Date.now();
            } else if (root.dragTime) {
                // Qt can end a drag without emitting flickStarted. Use the actual
                // content movement too, and do not coast after holding still.
                var speed = Date.now() - root.dragTime < 100 ? root.dragSpeed : 0;
                root.dragTime = 0;
                root.coast(speed);
            }
        }
        function onFlickStarted() {
            if (motion.running) root.target.cancelFlick();
            else root.coast(root.target.verticalVelocity);
        }
        function onContentYChanged() {
            if (root.target.dragging && root.dragTime) {
                var now = Date.now();
                var elapsed = now - root.dragTime;
                if (elapsed > 0) {
                    var speed = (root.target.contentY - root.dragY) * 1000 / elapsed;
                    root.dragSpeed = root.dragSpeed * 0.3 + speed * 0.7;
                    root.dragY = root.target.contentY;
                    root.dragTime = now;
                }
            }
            if (!motion.running) root.destination = root.clamp(root.target.contentY);
        }
        function onContentHeightChanged() { root.fitBounds(); }
        function onHeightChanged() { root.fitBounds(); }
        function onVisibleChanged() { if (!root.target.visible) root.stopMotion(); }
    }
    Connections {
        target: GlassTheme
        function onReducedMotionChanged() {
            if (GlassTheme.reducedMotion && root.target) {
                var end = root.destination;
                root.stopMotion();
                root.target.contentY = end;
            }
        }
    }
    FrameAnimation {
        id: motion
        onTriggered: {
            if (!root.enabled || !root.renderActive) { root.stopMotion(); return; }
            var dt = Math.min(0.05, Math.max(0.001, frameTime));
            var remaining = root.destination - root.target.contentY;
            if (Math.abs(remaining) < 0.4) {
                root.target.contentY = root.destination;
                stop();
            } else {
                root.target.contentY = root.clamp(root.target.contentY + remaining * (1 - Math.exp(-root.damping * dt)));
            }
        }
    }
    WheelHandler {
        parent: root.target
        enabled: root.enabled && root.renderActive && root.target.interactive
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(event) {
            var delta = event.pixelDelta.y ? -event.pixelDelta.y : -event.angleDelta.y / 120 * 92;
            var origin = motion.running ? root.destination : root.target.contentY;
            if (!delta || !root.maxY || (!motion.running && ((delta < 0 && origin <= 0) || (delta > 0 && origin >= root.maxY)))) {
                event.accepted = false;
                return;
            }
            event.accepted = true;
            root.scrollBy(delta, false);
        }
    }
}
