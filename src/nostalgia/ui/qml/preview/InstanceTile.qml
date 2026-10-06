import QtQuick
import "../" as Legacy

Rectangle {
    id: root
    property var entry: ({})
    property bool compact: false
    property bool selected: false
    property bool pickOnly: false
    signal editRequested(var entry)
    signal picked
    height: compact ? 92 : 204
    radius: 18
    color: hover.hovered ? GlassTheme.raised : GlassTheme.cardSurface
    border.color: selected ? GlassTheme.alpha(GlassTheme.accent, 0.65) : hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.40) : GlassTheme.stroke
    Behavior on color {
        ColorAnimation {
            duration: GlassTheme.quick
        }
    }
    readonly property string loader: (entry.versionId || "").indexOf("forge") >= 0 ? "Forge" : (entry.versionId || "").indexOf("fabric") >= 0 ? "Fabric" : "Vanilla"
    readonly property string version: (entry.versionId || "").split("-")[0]
    Rectangle {
        id: iconWell
        x: 20
        y: compact ? (parent.height - height) / 2 : 22
        width: compact ? 48 : 52
        height: width
        radius: 14
        color: GlassTheme.selectedSurface
        Legacy.BlockIcon {
            anchors.centerIn: parent
            width: 34
            height: 34
            block: root.loader === "Forge" ? "crafting" : "grass"
            glyph: "·"
        }
    }
    Column {
        x: root.compact ? 84 : 20
        y: root.compact ? 24 : 91
        width: root.width - x - (root.compact ? 214 : 20)
        spacing: 7
        Text {
            width: parent.width
            text: root.entry.label || root.entry.instanceId || ""
            color: GlassTheme.text
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontSubheading
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: root.version + "  ·  " + root.loader + (root.entry.groupName ? "  /  " + root.entry.groupName : "")
            color: GlassTheme.muted
            font.family: GlassTheme.font
            font.pixelSize: GlassTheme.fontLabel
            elide: Text.ElideRight
        }
    }
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.bottom: parent.bottom
        anchors.bottomMargin: root.compact ? 24 : 16
        spacing: 6
        Button {
            width: root.compact ? 84 : 75
            height: 36
            label: root.pickOnly ? (root.selected ? "Đã chọn" : "Chọn") : "Chơi"
            selected: root.selected
            clickable: root.pickOnly || (!!bridge.activePlayerName && !bridge.busy && !bridge.storageBusy && !bridge.gameRunning)
            onClicked: root.pickOnly ? root.picked() : bridge.play(root.entry.instanceId)
        }
        Button {
            visible: !root.pickOnly
            width: 38
            height: 36
            label: "···"
            quiet: true
            Accessible.name: "Quản lý " + (root.entry.label || "bản chơi")
            onClicked: root.editRequested(root.entry)
        }
    }
    Button {
        visible: !root.compact && !root.pickOnly
        x: parent.width - width - 16
        y: 18
        width: 32
        height: 32
        label: root.entry.favorite ? "★" : "☆"
        quiet: true
        Accessible.name: "Ghim " + (root.entry.label || "bản chơi")
        onClicked: storageBridge.setOrganization(root.entry.instanceId, root.entry.groupName || "", !root.entry.favorite)
    }
    HoverHandler {
        id: hover
    }
}
