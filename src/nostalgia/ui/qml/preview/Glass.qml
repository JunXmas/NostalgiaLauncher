import QtQuick
import QtQuick.Effects

Rectangle {
    id: root
    default property alias content: holder.data
    property int padding: 24
    property bool frosted: true
    property Item backdrop: GlassTheme.backdrop
    property rect backdropRect: Qt.rect(0, 0, -1, -1)
    property real blurOpacity: 0.60
    property int blurRadius: 48
    property real finishOpacity: 1
    readonly property bool shaderAvailable: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    radius: 24
    color: GlassTheme.glassSurface
    border.width: 1
    border.color: GlassTheme.stroke
    // Nguồn phải nằm ngoài panel để không thu lại chính hiệu ứng kính.
    ShaderEffectSource {
        id: capture
        anchors.fill: parent
        visible: false
        sourceItem: root.backdrop
        sourceRect: {
            if (root.backdropRect.width >= 0)
                return root.backdropRect;
            if (!root.backdrop)
                return Qt.rect(0, 0, 1, 1);
            // Follow the shared entrance transform without polling while idle.
            var entranceOffset = GlassTheme.pageMotion;
            var ancestor = root;
            while (ancestor) {
                var position = ancestor.x + ancestor.y + ancestor.width + ancestor.height + ancestor.scale;
                ancestor = ancestor.parent;
            }
            var p = root.mapToItem(root.backdrop, 0, 0);
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
        blurMax: root.blurRadius
        blur: 0.8
        saturation: -0.15
        maskEnabled: true
        maskSource: maskCapture
        opacity: root.blurOpacity
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
        opacity: root.finishOpacity
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
