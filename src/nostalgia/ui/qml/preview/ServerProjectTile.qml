import QtQuick
Item {
    id: root
    property var project: ({})
    property bool clickable: true
    signal chosen
    height: 210 * GlassTheme.scale
    Image {
        id: artwork; objectName: "serverProjectArtwork-" + root.project.project_id
        anchors.fill: parent; source: root.visible ? root.project.icon_url || "" : ""
        visible: false; asynchronous: true; cache: true; sourceSize.width: 320; sourceSize.height: 320
        fillMode: Image.PreserveAspectCrop
    }
    Glass {
        anchors.fill: parent; padding: 18; backdrop: artwork
        backdropRect: Qt.rect(0, 0, root.width, root.height)
        blurRadius: 32; blurOpacity: 0.28; radius: 20
        border.color: hover.hovered ? GlassTheme.alpha(GlassTheme.accent, 0.50) : GlassTheme.stroke
        color: GlassTheme.alpha(GlassTheme.surface, 0.50)
        transform: Translate { y: hover.hovered && !GlassTheme.reducedMotion ? -3 : 0; Behavior on y { NumberAnimation { duration: GlassTheme.quick } } }
        Row {
            width: parent.width; spacing: 12
            Rectangle { width: 44 * GlassTheme.scale; height: width; radius: 12; color: GlassTheme.alpha(GlassTheme.raised, 0.50)
                Image { objectName: "serverProjectIcon-" + root.project.project_id; anchors.fill: parent; anchors.margins: 3; source: root.visible ? root.project.icon_url || "" : ""; asynchronous: true; cache: true; sourceSize.width: 96; sourceSize.height: 96; fillMode: Image.PreserveAspectFit }
                PaymentText { visible: !root.project.icon_url; anchors.centerIn: parent; text: (root.project.title || "?").slice(0, 1); font.pixelSize: GlassTheme.fontTitle }
            }
            Column { width: parent.width - 44 * GlassTheme.scale - 12; spacing: 4
                PaymentText { width: parent.width; text: root.project.title || ""; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold; maximumLineCount: 1; elide: Text.ElideRight }
                PaymentText { text: root.project.source === "hangar" ? "Hangar · PaperMC" : "Modrinth"; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
            }
        }
        PaymentText { width: parent.width; y: 62 * GlassTheme.scale; text: root.project.description || ""; color: GlassTheme.muted; maximumLineCount: 3; elide: Text.ElideRight; font.pixelSize: GlassTheme.fontCaption }
        Button { objectName: "serverProject-" + root.project.project_id; anchors.bottom: parent.bottom; label: "Chọn phiên bản"; clickable: root.clickable; onClicked: root.chosen() }
    }
    HoverHandler { id: hover }
}
