import QtQuick
import "../" as Legacy

Glass {
    id: root
    padding: 0
    backdrop: Legacy.Theme.modalBackdrop
    frosted: visible
    blurRadius: 64
    blurOpacity: 0.92
    finishOpacity: 0.45
    color: "transparent"
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: GlassTheme.alpha(GlassTheme.surface, root.shaderAvailable ? 0.58 : 0.97)
        border.color: GlassTheme.alpha(GlassTheme.text, 0.14)
    }
}
