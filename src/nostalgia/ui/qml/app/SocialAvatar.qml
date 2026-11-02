import QtQuick
import "../" as Legacy
import QtQuick.Effects
import "CosmeticCatalog.js" as Cosmetics

Item {
    id: root
    property string playerName: ""
    property string source: ""
    property string decor: "none"
    property bool online: false
    property bool showPresence: true
    property bool clickable: false
    property int size: 40
    signal clicked
    width: size; height: size
    readonly property bool decorated: !!Cosmetics.find(decor, cosmeticBridge.sets)
    readonly property bool shaderAvailable: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    readonly property real faceSize: decorated ? size * 0.70 : size
    readonly property color tint: decorated ? Cosmetics.find(decor, cosmeticBridge.sets).tint : GlassTheme.accent
    Rectangle {
        anchors.centerIn: parent; width: root.faceSize; height: width; radius: width / 2
        color: GlassTheme.alpha(root.tint, 0.16)
        border.color: GlassTheme.stroke
        Text { anchors.centerIn: parent; text: root.playerName.slice(0, 1).toUpperCase() || "?"; color: GlassTheme.text; font.family: GlassTheme.displayFont; font.pixelSize: root.faceSize * 0.42; font.weight: Font.DemiBold }
    }
    Item {
        id: photo; anchors.centerIn: parent; width: root.faceSize - 4; height: width
        visible: avatarImage.status === Image.Ready
        clip: true
        layer.enabled: visible && root.shaderAvailable
        layer.effect: MultiEffect { maskEnabled: true; maskSource: maskCapture }
        Image { id: avatarImage; objectName: "socialAvatarImage"; anchors.fill: parent; source: root.visible ? root.source : ""; sourceSize: root.source.startsWith("data:image/png;base64,") ? Qt.size(8, 8) : Qt.size(128, 128); asynchronous: true; cache: true; smooth: !root.source.startsWith("data:image/png;base64,"); fillMode: Image.PreserveAspectCrop }
    }
    Rectangle { id: roundedMask; width: photo.width; height: photo.height; radius: width / 2; color: "white"; visible: root.shaderAvailable }
    ShaderEffectSource { id: maskCapture; anchors.fill: photo; sourceItem: roundedMask; hideSource: true; visible: false; live: root.visible && root.shaderAvailable }
    CosmeticFrame { objectName: "socialAvatarFrame"; anchors.fill: parent; decor: root.decor }
    Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; width: Math.max(10, root.size * 0.25); height: width; radius: width / 2; visible: root.showPresence; color: root.online ? GlassTheme.brand : GlassTheme.muted; border.width: 3; border.color: GlassTheme.surface }
    MouseArea { anchors.fill: parent; enabled: root.clickable; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
    activeFocusOnTab: clickable
    Accessible.role: Accessible.Button
    Accessible.name: Legacy.Tr.phrase("Hồ sơ của ") + playerName
    Accessible.onPressAction: if (clickable) root.clicked()
    Keys.onReturnPressed: if (clickable) root.clicked()
    Keys.onSpacePressed: if (clickable) root.clicked()
}
