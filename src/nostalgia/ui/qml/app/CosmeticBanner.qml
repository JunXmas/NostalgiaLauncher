import QtQuick
import QtQuick.Effects
import "CosmeticCatalog.js" as Cosmetics

Item {
    id: root
    property string decor: "none"
    property real radius: 18
    property bool scrim: true
    readonly property bool vector: Cosmetics.vector(decor, cosmeticBridge.sets)
    readonly property bool ready: vector ? vectorArt.available : art.status === Image.Ready
    readonly property bool shaderAvailable: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    Rectangle {
        anchors.fill: parent; radius: root.radius
        color: GlassTheme.alpha(GlassTheme.accent, 0.12)
    }
    Item {
        anchors.fill: parent
        clip: true
        layer.enabled: root.ready && root.shaderAvailable
        layer.effect: MultiEffect { maskEnabled: true; maskSource: maskCapture }
        Image {
            id: art; objectName: "cosmeticBannerImage"
            anchors.fill: parent
            source: root.visible ? Cosmetics.asset(root.decor, "banner", cosmeticBridge.sets) : ""
            sourceSize: Qt.size(Math.min(1536, Math.max(64, Math.ceil(width * Screen.devicePixelRatio))), 0)
            asynchronous: true; cache: true; smooth: true
            fillMode: Image.PreserveAspectCrop
        }
        VectorCosmetic { id: vectorArt; anchors.fill: parent; visible: root.vector; decor: root.decor; kind: "banner"; radius: root.radius }
        Rectangle {
            anchors.fill: parent; visible: root.scrim && root.ready
            gradient: Gradient { orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#d910101b" }
                GradientStop { position: 0.65; color: "#7a10101b" }
                GradientStop { position: 1; color: "#3510101b" }
            }
        }
    }
    Rectangle { id: roundedMask; width: root.width; height: root.height; radius: root.radius; color: "white"; visible: root.shaderAvailable }
    ShaderEffectSource { id: maskCapture; anchors.fill: parent; sourceItem: roundedMask; hideSource: true; visible: false; live: root.visible && root.shaderAvailable }
}
