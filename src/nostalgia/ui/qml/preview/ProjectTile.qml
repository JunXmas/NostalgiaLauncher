import QtQuick
import "../" as Legacy

Rectangle {
    id: tile
    property var project: ({})
    property bool compactScope: false
    property string contentKind: "modpack"
    property bool artworkEnabled: true
    signal modpackRequested(string projectId, string title)
    objectName: "projectCard-" + tile.project.projectId
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: tile.project.title + Legacy.Tr.phrase(", xem giới thiệu và phiên bản")
    Accessible.onPressAction: projectBridge.openProject(tile.project.projectId)
    Keys.onReturnPressed: projectBridge.openProject(tile.project.projectId)
    Keys.onEnterPressed: projectBridge.openProject(tile.project.projectId)
    width: 300
    height: (tile.compactScope ? 126 : 218) * GlassTheme.scale
    radius: 18
    color: hover.hovered ? GlassTheme.raised : GlassTheme.cardSurface
    Behavior on color {
        ColorAnimation {
            duration: GlassTheme.quick
        }
    }
    CardMica {
        objectName: "projectArtwork-" + tile.project.projectId
        source: tile.project.iconUrl
        radius: tile.radius
        renderEnabled: tile.artworkEnabled && tile.visible
    }
    Rectangle {
        anchors.fill: parent
        radius: tile.radius
        color: "transparent"
        border.color: hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.50) : GlassTheme.stroke
    }
    MouseArea {
        anchors.fill: parent
        onClicked: function (mouse) {
            if (mouse.x >= downloadButton.x && mouse.x <= downloadButton.x + downloadButton.width && mouse.y >= downloadButton.y && mouse.y <= downloadButton.y + downloadButton.height)
                return;
            tile.forceActiveFocus();
            projectBridge.openProject(tile.project.projectId);
        }
    }
    Legacy.ProjectIcon {
        id: projectIcon
        x: 20 * GlassTheme.scale
        y: 20 * GlassTheme.scale
        width: 52 * GlassTheme.scale
        height: width
        source: tile.project.iconUrl
        fallbackText: tile.project.title
    }
    Column {
        x: (tile.compactScope ? 90 : 20) * GlassTheme.scale
        y: (tile.compactScope ? 16 : 90) * GlassTheme.scale
        width: parent.width - x - 20 * GlassTheme.scale
        spacing: 8 * GlassTheme.scale
        Text {
            width: parent.width
            text: tile.project.title
            color: GlassTheme.text
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontSubheading
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: tile.project.description
            objectName: "projectDescription-" + tile.project.projectId
            color: Legacy.Theme.mix(GlassTheme.muted, GlassTheme.text, 0.15)
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontLabel
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
            lineHeight: 1.3
        }
    }
    Text {
        objectName: "projectMeta-" + tile.project.projectId
        width: Math.max(0, downloadButton.x - (tile.compactScope ? 100 : 30) * GlassTheme.scale)
        elide: Text.ElideRight
        anchors.left: parent.left
        anchors.leftMargin: (tile.compactScope ? 90 : 20) * GlassTheme.scale
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 25 * GlassTheme.scale
        text: Legacy.Theme.compact(tile.project.downloads) + Legacy.Tr.phrase(" tải  ·  ") + (tile.project.loaders.length ? tile.project.loaders[0] : "Minecraft")
        color: Legacy.Theme.mix(GlassTheme.muted, GlassTheme.text, 0.15)
        font.family: GlassTheme.font
        font.pixelSize: GlassTheme.fontNote
    }
    Button {
        id: downloadButton
        objectName: "projectDownload-" + tile.project.projectId
        anchors.right: parent.right
        anchors.rightMargin: 14 * GlassTheme.scale
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 16 * GlassTheme.scale
        label: tile.project.installing ? Legacy.Tr.phrase("Đang cài…") : tile.project.contentKind === "modpack" ? Legacy.Tr.phrase("Tạo bản chơi") : tile.project.installed ? Legacy.Tr.phrase("Đã cài") : Legacy.Tr.phrase("Cài đặt")
        height: 34 * GlassTheme.scale
        clickable: !tile.project.installing && !tile.project.installed && !contentBridge.busy && !bridge.gameRunning && !bridge.storageBusy && !bridge.busy && (tile.project.contentKind === "modpack" || (!!contentBridge.instanceId && !(tile.contentKind === "mod" && contentBridge.loaderKind === "vanilla")))
        onClicked: tile.project.contentKind === "modpack" ? tile.modpackRequested(tile.project.projectId, tile.project.title) : contentBridge.install(tile.project.projectId)
    }
    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }
}
