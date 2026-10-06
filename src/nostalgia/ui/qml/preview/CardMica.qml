import QtQuick
import QtQuick.Effects

Item {
    id: root
    property string source: ""
    property real radius: 18
    readonly property bool shaderAvailable: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    anchors.fill: parent
    // The original mica technique: blend two tiny, smoothly enlarged avatar images.
    // Software rendering keeps the imagery inside the rounded corners without shaders.
    Item {
        id: backdrop
        anchors.fill: parent
        anchors.margins: root.shaderAvailable ? 1 : root.radius
        clip: true
        opacity: base.status === Image.Ready ? 1 : 0
        Behavior on opacity {
            NumberAnimation {
                duration: GlassTheme.quick
            }
        }
        layer.enabled: root.shaderAvailable
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: maskCapture
        }
        Image {
            id: base
            anchors.right: parent.right
            width: parent.width * 0.85
            height: parent.height
            source: root.source
            sourceSize: Qt.size(4, 4)
            smooth: true
            asynchronous: true
            fillMode: Image.PreserveAspectCrop
            opacity: 0.8
        }
        Image {
            anchors.fill: base
            anchors.margins: -60
            source: root.source
            sourceSize: Qt.size(7, 7)
            smooth: true
            asynchronous: true
            fillMode: Image.PreserveAspectCrop
            opacity: 0.45
        }
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0
                    color: GlassTheme.surface
                }
                GradientStop {
                    position: 0.35
                    color: GlassTheme.alpha(GlassTheme.surface, 0.92)
                }
                GradientStop {
                    position: 0.7
                    color: GlassTheme.alpha(GlassTheme.surface, 0.65)
                }
                GradientStop {
                    position: 1
                    color: GlassTheme.alpha(GlassTheme.surface, 0.30)
                }
            }
        }
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop {
                    position: 0
                    color: GlassTheme.alpha(GlassTheme.surface, root.shaderAvailable ? 0.12 : 1)
                }
                GradientStop {
                    position: 0.18
                    color: "transparent"
                }
                GradientStop {
                    position: 0.42
                    color: GlassTheme.alpha(GlassTheme.surface, 0.55)
                }
                GradientStop {
                    position: 0.72
                    color: GlassTheme.alpha(GlassTheme.surface, 0.65)
                }
                GradientStop {
                    position: 1
                    color: GlassTheme.alpha(GlassTheme.surface, root.shaderAvailable ? 0.80 : 1)
                }
            }
        }
    }
    Rectangle {
        id: mask
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, root.radius - 1)
        color: "white"
        visible: root.shaderAvailable
    }
    ShaderEffectSource {
        id: maskCapture
        anchors.fill: mask
        sourceItem: mask
        hideSource: true
        visible: false
        live: root.visible && root.shaderAvailable
    }
}
