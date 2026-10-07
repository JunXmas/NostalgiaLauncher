import QtQuick
import QtQuick.Window

/* Mesh 3D đúng UV Steve/Alex; ảnh chiếu được dựng ở worker Qt, cache có giới hạn.
   Không đồng hồ chạy nền. Chỉ đổi frame khi người dùng xoay hoặc nhấn đổi hướng. */
Item {
    id: root
    property string source: ""
    property bool slim: false
    property string revision: ""
    property int facing: 0
    property real pixel: 6
    property real yaw: 25
    property bool interactive: true
    property bool renderEnabled: true
    property bool componentReady: false
    readonly property int frame: ((Math.round(yaw / 5) % 72) + 72) % 72
    readonly property bool renderActive: renderEnabled && visible && source !== "" &&
        Window.window && Window.window.visible && Window.window.visibility !== Window.Minimized
    readonly property string previewKey: source + (slim ? "|1|" : "|0|") + revision
    readonly property string thumbnail: skinPreviews ? (skinPreviews.previews[previewKey] || "") : ""
    readonly property string atlas: skinPreviews ? (skinPreviews.atlases[previewKey] || "") : ""
    readonly property bool atlasReady: atlasImage.status === Image.Ready
    readonly property bool ready: skinImage.status === Image.Ready || atlasReady
    function requestPreview() {
        if (componentReady && renderActive && skinPreviews) skinPreviews.ensurePreview(source, slim, revision, interactive);
    }
    function schedulePreview() { if (componentReady) Qt.callLater(root.requestPreview); }
    Component.onCompleted: { componentReady = true; schedulePreview(); }
    onRenderActiveChanged: schedulePreview()
    onSourceChanged: schedulePreview()
    onSlimChanged: schedulePreview()
    onRevisionChanged: schedulePreview()
    onInteractiveChanged: schedulePreview()
    width: pixel * 16
    height: pixel * 32
    clip: true
    activeFocusOnTab: interactive
    onFacingChanged: yaw = 25 + facing * 90
    Behavior on yaw {
        enabled: !rotationArea.pressed && root.renderActive && !Theme.reducedMotion
        NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic }
    }
    Image {
        id: skinImage
        objectName: "skin3DImage"
        anchors.fill: parent
        source: root.renderActive ? root.thumbnail : ""
        visible: !root.atlasReady
        asynchronous: true
        cache: false
        sourceSize: Qt.size(Math.ceil(root.width), Math.ceil(root.height))
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
    Image {
        id: atlasImage
        objectName: "skin3DAtlas"
        source: root.renderActive && root.interactive ? root.atlas : ""
        width: root.width * 12
        height: root.height * 6
        x: -(root.frame % 12) * root.width
        y: -Math.floor(root.frame / 12) * root.height
        visible: root.atlasReady
        asynchronous: true
        cache: false
        smooth: true
    }
    MouseArea {
        id: rotationArea
        objectName: "skinRotationArea"
        anchors.fill: parent
        enabled: root.interactive
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property real pressX: 0
        property real pressYaw: 0
        onPressed: function(mouse) {
            root.forceActiveFocus();
            pressX = mouse.x;
            pressYaw = root.yaw;
        }
        onPositionChanged: function(mouse) {
            if (pressed) root.yaw = pressYaw + (mouse.x - pressX) * 0.9;
        }
    }
    Keys.onLeftPressed: yaw -= 30
    Keys.onRightPressed: yaw += 30
}
