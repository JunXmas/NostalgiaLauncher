import QtQuick
import QtQuick.Effects

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
    readonly property color tint: decor === "emerald" ? "#60ae7b" : decor === "amber" ? "#daa86c" : "#b66ba9"
    Rectangle {
        anchors.fill: parent; radius: width / 2
        color: GlassTheme.alpha(root.tint, 0.16)
        border.color: root.decor !== "none" ? root.tint : GlassTheme.stroke
        border.width: root.decor !== "none" ? 2 : 1
        Text { anchors.centerIn: parent; text: root.playerName.slice(0, 1).toUpperCase() || "?"; color: GlassTheme.text; font.family: GlassTheme.displayFont; font.pixelSize: root.size * 0.42; font.weight: Font.DemiBold }
    }
    Item {
        id: photo; anchors.fill: parent; anchors.margins: root.decor !== "none" ? 4 : 2
        visible: avatarImage.status === Image.Ready
        layer.enabled: visible
        layer.effect: MultiEffect { maskEnabled: true; maskSource: roundedMask }
        Image { id: avatarImage; objectName: "socialAvatarImage"; anchors.fill: parent; source: root.visible ? root.source : ""; sourceSize: root.source.startsWith("data:image/png;base64,") ? Qt.size(8, 8) : Qt.size(128, 128); asynchronous: true; cache: true; smooth: !root.source.startsWith("data:image/png;base64,"); fillMode: Image.PreserveAspectCrop }
    }
    Item { id: roundedMask; width: photo.width; height: photo.height; visible: false; layer.enabled: true
        Rectangle { anchors.fill: parent; radius: width / 2; color: "white" }
    }
    Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; width: Math.max(10, root.size * 0.25); height: width; radius: width / 2; visible: root.showPresence; color: root.online ? GlassTheme.brand : GlassTheme.muted; border.width: 3; border.color: GlassTheme.surface }
    MouseArea { anchors.fill: parent; enabled: root.clickable; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
    activeFocusOnTab: clickable
    Accessible.role: Accessible.Button
    Accessible.name: "Hồ sơ của " + playerName
    Accessible.onPressAction: if (clickable) root.clicked()
    Keys.onReturnPressed: if (clickable) root.clicked()
    Keys.onSpacePressed: if (clickable) root.clicked()
}
