import QtQuick
import QtQuick.Window

Item {
    id: root
    objectName: "homeDiorama"
    readonly property bool animated: visible && Window.window && Window.window.active && !GlassTheme.reducedMotion
    property real bob: 0
    readonly property real sway: hover.hovered && animated ? (hover.point.position.x / width - 0.5) * 12 : 0
    Image {
        width: parent.width * 1.4
        height: width
        anchors.centerIn: parent
        source: "../assets/glow.png"
        opacity: 0.18
        smooth: true
    }
    Rectangle {
        x: parent.width * 0.24
        y: parent.height * 0.87
        width: parent.width * 0.52
        height: 18
        radius: 9
        color: "#22040b06"
    }
    Image {
        id: island
        objectName: "homeIslandImage"
        width: Math.min(parent.width + 24, parent.height * 1.08)
        height: width
        x: (parent.width - width) / 2 + root.sway
        y: (parent.height - height) / 2 + root.bob
        source: "../assets/home-island.png"
        fillMode: Image.PreserveAspectFit
        mipmap: true
        Behavior on x {
            enabled: root.animated
            NumberAnimation {
                duration: GlassTheme.reducedMotion ? 0 : 240
                easing.type: Easing.OutCubic
            }
        }
    }
    Repeater {
        model: [
            {
                x: 0.13,
                y: 0.26,
                delay: 0
            },
            {
                x: 0.79,
                y: 0.42,
                delay: 800
            },
            {
                x: 0.23,
                y: 0.72,
                delay: 1600
            }
        ]
        Rectangle {
            x: root.width * modelData.x
            y: root.height * modelData.y - root.bob * 0.7
            width: 3
            height: 3
            radius: 1.5
            color: "#e4e6a0"
            opacity: 0.32
            SequentialAnimation on opacity {
                running: root.animated
                loops: Animation.Infinite
                PauseAnimation {
                    duration: modelData.delay
                }
                NumberAnimation {
                    to: 0.65
                    duration: 2600
                    easing.type: Easing.InOutSine
                }
                NumberAnimation {
                    to: 0.15
                    duration: 2600
                    easing.type: Easing.InOutSine
                }
            }
        }
    }
    SequentialAnimation on bob {
        running: root.animated
        loops: Animation.Infinite
        NumberAnimation {
            to: -5
            duration: 4400
            easing.type: Easing.InOutSine
        }
        NumberAnimation {
            to: 0
            duration: 4400
            easing.type: Easing.InOutSine
        }
    }
    onAnimatedChanged: if (!animated)
        bob = 0
    HoverHandler {
        id: hover
    }
}
