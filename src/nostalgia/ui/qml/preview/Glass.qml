import QtQuick
import QtQuick.Effects

Rectangle {
    id: root
    default property alias content: holder.data
    property int padding: 24
    property bool frosted: true
    readonly property bool shaderAvailable: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    radius: 24
    color: GlassTheme.glassSurface
    border.width: 1
    border.color: GlassTheme.stroke
    // Capture only the dedicated background, never the pane itself (no recursion).
    ShaderEffectSource {
        id: capture
        anchors.fill: parent
        visible: false
        sourceItem: GlassTheme.backdrop
        sourceRect: {
            if (!GlassTheme.backdrop)
                return Qt.rect(0, 0, 1, 1);
            var p = root.mapToItem(GlassTheme.backdrop, 0, 0);
            return Qt.rect(p.x, p.y, root.width, root.height);
        }
        textureSize: Qt.size(Math.max(1, root.width / 2), Math.max(1, root.height / 2))
        live: root.visible && root.frosted && root.shaderAvailable
        hideSource: false
    }
    MultiEffect {
        objectName: "glassEffect"
        anchors.fill: parent
        visible: root.frosted && root.shaderAvailable
        source: capture
        blurEnabled: true
        blurMax: 48
        blur: 0.8
        saturation: -0.15
        maskEnabled: true
        maskSource: maskCapture
        opacity: 0.60
    }
    Rectangle {
        id: mask
        anchors.fill: parent
        radius: root.radius
        color: "white"
        visible: root.shaderAvailable
    }
    ShaderEffectSource {
        id: maskCapture
        sourceItem: mask
        hideSource: true
        visible: false
        anchors.fill: parent
        live: root.visible && root.frosted && root.shaderAvailable
    }
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        gradient: Gradient {
            GradientStop {
                position: 0
                color: GlassTheme.alpha(GlassTheme.raised, 0.40)
            }
            GradientStop {
                position: 0.45
                color: GlassTheme.alpha(GlassTheme.surface, 0.03)
            }
            GradientStop {
                position: 1
                color: GlassTheme.alpha(GlassTheme.background, 0.51)
            }
        }
        border.color: GlassTheme.alpha(GlassTheme.text, 0.10)
    }
    Item {
        id: holder
        anchors.fill: parent
        anchors.margins: root.padding
    }
}
