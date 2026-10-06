import QtQuick

Item {
    id: root
    property bool cinematic: false
    Rectangle {
        anchors.fill: parent
        color: GlassTheme.background
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
                color: "#b00c1014"
            }
            GradientStop {
                position: 0.6
                color: "#000c1014"
            }
            GradientStop {
                position: 1
                color: "#990c1014"
            }
        }
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop {
                position: 0
                color: "#000c1014"
            }
            GradientStop {
                position: 0.65
                color: "#350c1014"
            }
            GradientStop {
                position: 1
                color: "#ed0c1014"
            }
        }
    }
}
