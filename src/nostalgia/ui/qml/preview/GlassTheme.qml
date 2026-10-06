pragma Singleton
import QtQuick

QtObject {
    readonly property color background: "#0c1014"
    readonly property color surface: "#181e23"
    readonly property color raised: "#20282e"
    readonly property color stroke: "#22ffffff"
    readonly property color text: "#f1f5f3"
    readonly property color muted: "#a0abae"
    readonly property color accent: "#75e5b4"
    readonly property color ink: "#09241a"
    readonly property string font: "Inter"
    property var preferences: null
    readonly property bool reducedMotion: preferences ? preferences.reducedMotion : false
    readonly property real scale: preferences ? preferences.uiScale / 100 : 1
    readonly property int quick: reducedMotion ? 0 : 160
    property var backdrop: null
}
