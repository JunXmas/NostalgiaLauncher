import QtQuick

Item {
    id: root
    property bool cinematic: false
    Rectangle {
        anchors.fill: parent
        color: GlassTheme.canvas
    }
    Image {
        anchors.fill: parent
        source: "../assets/hero.jpg"
        visible: root.cinematic
        fillMode: Image.PreserveAspectCrop
        mipmap: true
        opacity: 0.25
    }
    Image {
        x: parent.width * 0.20
        y: -height * 0.38
        width: parent.width * 1.10
        height: width
        source: "../assets/glow.png"
        smooth: true
        opacity: root.cinematic ? 0.26 : 0.14
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: GlassTheme.alpha(GlassTheme.background, 0.69)
            }
            GradientStop {
                position: 0.6
                color: GlassTheme.alpha(GlassTheme.background, 0)
            }
            GradientStop {
                position: 1
                color: GlassTheme.alpha(GlassTheme.background, 0.60)
            }
        }
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop {
                position: 0
                color: GlassTheme.alpha(GlassTheme.background, 0)
            }
            GradientStop {
                position: 0.65
                color: GlassTheme.alpha(GlassTheme.background, 0.21)
            }
            GradientStop {
                position: 1
                color: GlassTheme.alpha(GlassTheme.background, 0.93)
            }
        }
    }
}
