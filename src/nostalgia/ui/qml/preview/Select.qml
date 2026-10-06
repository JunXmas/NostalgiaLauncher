import QtQuick
import QtQuick.Controls as Controls

Controls.ComboBox {
    id: root
    height: 42 * GlassTheme.scale
    font.family: GlassTheme.font
    font.pixelSize: 13 * GlassTheme.scale
    background: Rectangle {
        radius: 12
        color: "#80192328"
        border.color: root.activeFocus ? GlassTheme.accent : GlassTheme.stroke
    }
    contentItem: Text {
        leftPadding: 14
        rightPadding: 30
        verticalAlignment: Text.AlignVCenter
        text: root.displayText
        color: GlassTheme.muted
        font: root.font
        elide: Text.ElideRight
    }
    indicator: Text {
        x: root.width - 26
        anchors.verticalCenter: parent.verticalCenter
        text: "⌄"
        color: GlassTheme.muted
        font.pixelSize: 16
    }
    delegate: Controls.ItemDelegate {
        width: root.width
        text: modelData
        font: root.font
        contentItem: Text {
            text: modelData
            color: highlighted ? GlassTheme.accent : GlassTheme.text
            font: root.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: highlighted ? "#233e34" : GlassTheme.surface
            radius: 8
        }
    }
    popup.background: Rectangle {
        color: GlassTheme.surface
        radius: 12
        border.color: GlassTheme.stroke
    }
}
