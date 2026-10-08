import QtQuick
import QtQuick.Effects

Item {
    id: root
    property string gameVersion: ""
    readonly property string major: gameVersion.startsWith("1.") ? gameVersion.split(".").slice(0, 2).join(".") : gameVersion.split(".")[0]
    readonly property var titles: ({"26": "Wilderness Bound", "1.21": "Tricky Trials", "1.20": "Trails & Tales", "1.19": "The Wild Update", "1.18": "Caves & Cliffs II", "1.17": "Caves & Cliffs I", "1.16": "Nether Update", "1.15": "Buzzy Bees", "1.14": "Village & Pillage", "1.13": "Update Aquatic", "1.12": "World of Color", "1.11": "Exploration Update", "1.10": "Frostburn Update", "1.9": "Combat Update", "1.8": "Bountiful Update"})
    readonly property string title: titles[major] || "Minecraft: Java Edition"
    readonly property url artSource: Qt.resolvedUrl("../assets/keyart/" + (titles[major] ? major : "old") + ".jpg")
    readonly property bool ready: artwork.ready
    readonly property bool shaderAvailable: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    implicitHeight: width / 2.56
    height: implicitHeight
    Accessible.ignored: true
    Rectangle { anchors.fill: parent; radius: 16; color: GlassTheme.cardSurface }
    ArtworkTransition {
        id: artwork
        imageObjectName: "createKeyArtImage"
        anchors.fill: parent; anchors.margins: root.shaderAvailable ? 0 : 6
        source: root.artSource; active: root.visible
        decodeWidth: Math.min(1024, Math.max(64, Math.ceil(root.width * Screen.devicePixelRatio)))
        fillMode: Image.PreserveAspectFit
        layer.enabled: root.shaderAvailable && root.ready
        layer.effect: MultiEffect { maskEnabled: true; maskSource: maskCapture }
    }
    Rectangle { id: roundedMask; anchors.fill: parent; radius: 16; color: "white"; visible: root.shaderAvailable }
    ShaderEffectSource { id: maskCapture; anchors.fill: parent; sourceItem: roundedMask; hideSource: true; visible: false; live: root.visible && root.shaderAvailable }
    Rectangle { anchors.fill: parent; radius: 16; color: "transparent"; border.color: GlassTheme.stroke }
}
