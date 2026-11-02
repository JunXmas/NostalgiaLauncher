import QtQuick
import "../" as Legacy

Glass {
    id: root
    objectName: "localProfileStats"
    property var stats: ({})
    padding: 18
    height: body.implicitHeight + 36
    Column {
        id: body
        width: parent.width
        spacing: 16
        PaymentText { text: Legacy.Tr.phrase("THỐNG KÊ TRÊN MÁY NÀY"); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
        Grid {
            id: grid
            width: parent.width
            columns: width < 560 * GlassTheme.scale ? 2 : 4
            spacing: 14
            Repeater {
                model: [
                    {label: "Thời gian chơi", value: Legacy.Tr.message(root.stats.playtime || "chưa chơi")},
                    {label: "Lượt chơi", value: root.stats.launches || 0},
                    {label: "Thế giới", value: root.stats.worlds || 0},
                    {label: "Bản chơi", value: root.stats.instances || 0}
                ]
                Column {
                    required property var modelData
                    width: (grid.width - (grid.columns - 1) * grid.spacing) / grid.columns
                    spacing: 6
                    PaymentText { width: parent.width; text: modelData.value; font.pixelSize: GlassTheme.fontSubheading; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase(modelData.label); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                }
            }
        }
        PaymentText { width: parent.width; visible: !!root.stats.favoriteVersion; text: Legacy.Tr.phrase("Phiên bản chơi nhiều nhất: ") + (root.stats.favoriteVersion || ""); color: GlassTheme.muted }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Chỉ lưu trên máy này. Bạn bè không thấy số liệu này."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
    }
}
