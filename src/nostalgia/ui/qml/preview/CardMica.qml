import QtQuick

Item {
    id: root
    property string source: ""
    property real radius: 18
    property bool renderEnabled: visible
    readonly property bool ready: artwork.status === Image.Ready
    readonly property bool shaderAvailable: surface.shaderAvailable
    anchors.fill: parent
    Image {
        id: artwork
        objectName: "cardArtwork"
        anchors.fill: parent
        source: root.renderEnabled ? root.source : ""
        sourceSize: Qt.size(160, 160)
        visible: false; asynchronous: true; cache: true
        fillMode: Image.PreserveAspectCrop
        onSourceChanged: Qt.callLater(function() { if (surface && typeof surface.refreshBackdrop === "function") surface.refreshBackdrop(); })
        onStatusChanged: if (status === Image.Ready) Qt.callLater(function() { if (surface && typeof surface.refreshBackdrop === "function") surface.refreshBackdrop(); })
    }
    Image {
        anchors.fill: parent; anchors.margins: root.radius
        visible: !root.shaderAvailable
        source: root.renderEnabled && !root.shaderAvailable ? root.source : ""
        sourceSize: Qt.size(4, 4); smooth: true; asynchronous: true; cache: true
        fillMode: Image.PreserveAspectCrop; opacity: 0.18
    }
    Glass {
        id: surface
        objectName: "cardArtworkGlass"
        anchors.fill: parent; padding: 0; radius: root.radius
        backdrop: root.renderEnabled && root.ready ? artwork : null
        backdropRect: Qt.rect(0, 0, root.width, root.height)
        frosted: root.renderEnabled && root.ready
        liveBackdrop: false
        blurRadius: 32; blurOpacity: 0.28
        color: GlassTheme.alpha(GlassTheme.surface, 0.50)
        opacity: root.renderEnabled ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: GlassTheme.quick } }
    }
}
