import QtQuick
import "../" as Legacy

Grid {
    id: root
    property int currentStep: 0
    columns: width < 460 * GlassTheme.scale ? 1 : 3
    columnSpacing: 8; rowSpacing: 8
    Repeater {
        model: [Legacy.Tr.phrase("Chọn bản chơi"), Legacy.Tr.phrase("Mời & đồng bộ"), Legacy.Tr.phrase("Mở world & LAN")]
        Rectangle {
            required property int index
            required property string modelData
            readonly property bool current: index === root.currentStep
            readonly property bool complete: index < root.currentStep
            width: (root.width - (root.columns - 1) * root.columnSpacing) / root.columns
            height: Math.max(40 * GlassTheme.scale, caption.implicitHeight + 20)
            radius: 10
            color: GlassTheme.alpha(GlassTheme.accent, current ? 0.16 : 0.04)
            border.color: GlassTheme.alpha(current ? GlassTheme.accent : GlassTheme.stroke, current ? 0.6 : 0.5)
            Behavior on color { ColorAnimation { duration: GlassTheme.normal } }
            PaymentText {
                id: caption
                x: 10; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 20
                text: (parent.complete ? "✓" : (index + 1)) + "  " + modelData
                color: parent.current ? GlassTheme.text : parent.complete ? GlassTheme.brand : GlassTheme.muted
                font.pixelSize: GlassTheme.fontLabel; font.weight: parent.current ? Font.DemiBold : Font.Normal
            }
        }
    }
}
