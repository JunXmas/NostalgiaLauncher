import QtQuick
import "GuideCatalog.js" as Guides

Rectangle {
    id: root
    property string topicId: "start"
    readonly property var topic: Guides.find(topicId)
    readonly property bool stacked: width < 480 * GlassTheme.scale
    objectName: "guideCard-" + topicId
    radius: 14
    color: GlassTheme.alpha(GlassTheme.accent, 0.055)
    border.color: GlassTheme.alpha(GlassTheme.accent, 0.16)
    implicitHeight: copy.implicitHeight + 28 + (stacked ? openGuide.height + 8 : 0)
    height: implicitHeight
    Column {
        id: copy; x: 14; y: 14; spacing: 5
        width: root.width - 28 - (root.stacked ? 0 : openGuide.width + 20)
        PaymentText { width: parent.width; text: root.topic.title; font.weight: Font.DemiBold; font.pixelSize: GlassTheme.fontBody }
        PaymentText { width: parent.width; text: root.topic.summary; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
    }
    GuideButton {
        id: openGuide; topicId: root.topicId
        anchors.right: parent.right; anchors.rightMargin: 12
        y: root.stacked ? copy.y + copy.height + 8 : (root.height - height) / 2
        height: 34 * GlassTheme.scale
    }
}
