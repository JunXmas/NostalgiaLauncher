import QtQuick
import "../" as Legacy

Rectangle {
    id: root
    property var content: ({})
    property string selectionName: "selectSync_" + (root.content.path || "")
    property bool selected: false
    property bool interactive: true
    signal toggled(bool selected)
    width: parent ? parent.width : 440
    height: 72 * GlassTheme.scale
    radius: 14; clip: true
    color: GlassTheme.alpha(GlassTheme.surface, 0.6)
    border.color: GlassTheme.alpha(GlassTheme.accent, root.selected ? 0.30 : 0.08)
    Behavior on border.color { ColorAnimation { duration: GlassTheme.quick } }
    CardMica {
        objectName: "syncContentMica"
        radius: root.radius
        source: root.content.icon || fallback.source
        renderEnabled: root.visible
    }
    Rectangle {
        x: 12; anchors.verticalCenter: parent.verticalCenter
        width: 40 * GlassTheme.scale; height: width; radius: 10
        color: GlassTheme.alpha(GlassTheme.surface, 0.65)
        Legacy.BlockIcon { id: fallback; anchors.fill: parent; anchors.margins: 5; block: "bookshelf"; glyph: "▧"; visible: icon.status !== Image.Ready }
        Image {
            id: icon
            anchors.fill: parent; anchors.margins: 3
            source: root.content.icon || ""; sourceSize: Qt.size(96, 96)
            asynchronous: true; fillMode: Image.PreserveAspectFit
        }
    }
    Legacy.CheckRow {
        id: selection
        objectName: root.selectionName
        x: 66 * GlassTheme.scale; y: 12 * GlassTheme.scale
        width: root.width - x - 16; label: root.content.title || ""
        checked: root.selected; enabled: root.interactive
        onToggled: function(checked) { root.toggled(checked); }
    }
    PaymentText {
        x: selection.x; y: selection.y + selection.height + 3
        width: selection.width; wrapMode: Text.NoWrap; elide: Text.ElideRight
        font.pixelSize: GlassTheme.fontCaption; color: GlassTheme.muted
        text: (root.content.added ? Legacy.Tr.phrase("Mới · ") : "") + (root.content.enabled === false ? Legacy.Tr.phrase("Đang tắt · ") : "") + (root.content.path || "").split("/").pop().replace(/\.disabled$/, "")
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    opacity: root.selected ? 1 : 0.7
    Behavior on opacity { NumberAnimation { duration: GlassTheme.quick } }
}
