import QtQuick
import QtQuick.Shapes

Item {
    id: root
    objectName: "buttonSymbol"
    property string symbol: ""
    property color color: GlassTheme.text
    width: 20; height: 20
    Shape {
        anchors.fill: parent
        visible: root.symbol === "close"
        ShapePath {
            strokeColor: root.color; strokeWidth: 2
            capStyle: ShapePath.RoundCap; fillColor: "transparent"
            startX: 5; startY: 5
            PathLine { x: 15; y: 15 }
            PathMove { x: 15; y: 5 }
            PathLine { x: 5; y: 15 }
        }
    }
    Row {
        anchors.centerIn: parent; spacing: 3
        visible: root.symbol === "more"
        Repeater { model: 3; Rectangle { width: 3; height: 3; radius: 1.5; color: root.color } }
    }
    Shape {
        anchors.fill: parent
        visible: root.symbol === "star" || root.symbol === "star-filled"
        ShapePath {
            strokeColor: root.color; strokeWidth: 1.5
            joinStyle: ShapePath.RoundJoin
            fillColor: root.symbol === "star-filled" ? root.color : "transparent"
            startX: 10; startY: 1.5
            PathLine { x: 12.6; y: 6.7 }
            PathLine { x: 18.4; y: 7.5 }
            PathLine { x: 14.2; y: 11.6 }
            PathLine { x: 15.2; y: 17.4 }
            PathLine { x: 10; y: 14.6 }
            PathLine { x: 4.8; y: 17.4 }
            PathLine { x: 5.8; y: 11.6 }
            PathLine { x: 1.6; y: 7.5 }
            PathLine { x: 7.4; y: 6.7 }
            PathLine { x: 10; y: 1.5 }
        }
    }
}
