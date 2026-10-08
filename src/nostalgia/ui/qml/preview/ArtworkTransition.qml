import QtQuick

Item {
    id: root
    property url source
    property bool active: visible
    property int fillMode: Image.PreserveAspectFit
    property int decodeWidth: 1024
    property string imageObjectName: ""
    readonly property bool ready: current.status === Image.Ready || (blend < 1 && previous.status === Image.Ready)
    readonly property bool transitioning: fade.running
    property url settledSource: ""
    property real blend: 0
    function settle() {
        fade.stop();
        blend = current.status === Image.Ready ? 1 : 0;
        if (current.status === Image.Ready) settledSource = current.source;
    }
    onActiveChanged: {
        if (!active) { fade.stop(); blend = 0; settledSource = ""; }
    }
    Image {
        id: previous
        anchors.fill: parent
        source: root.active && root.blend < 1 ? root.settledSource : ""
        sourceSize: current.sourceSize
        fillMode: root.fillMode; asynchronous: true; cache: true
    }
    Image {
        id: current
        objectName: root.imageObjectName
        anchors.fill: parent
        source: root.active ? root.source : ""
        sourceSize: Qt.size(root.decodeWidth, 0)
        fillMode: root.fillMode; asynchronous: true; cache: true
        opacity: root.blend
        onSourceChanged: { fade.stop(); root.blend = 0; }
        onStatusChanged: {
            if (status === Image.Ready && root.active) {
                if (GlassTheme.reducedMotion) root.settle();
                else fade.restart();
            }
        }
    }
    NumberAnimation {
        id: fade; objectName: "artworkFade"
        target: root; property: "blend"; from: 0; to: 1
        duration: GlassTheme.slow; easing.type: Easing.OutCubic
        onFinished: root.settledSource = current.source
    }
    Connections {
        target: GlassTheme
        function onReducedMotionChanged() { if (GlassTheme.reducedMotion) root.settle(); }
    }
}
