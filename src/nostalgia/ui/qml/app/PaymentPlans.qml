import QtQuick
import "../" as Legacy

Column {
    id: root
    spacing: 10
    readonly property bool lifetime: paymentBridge.details.lifetime === true
    Grid {
        id: grid
        width: parent.width
        columns: width > 420 * GlassTheme.scale ? 2 : 1
        spacing: 10
        Repeater {
            model: [{lifetime: false, duration: Legacy.Tr.phrase("1 năm"), price: Legacy.Tr.phrase("79.000đ")},
                    {lifetime: true, duration: Legacy.Tr.phrase("Mua đứt"), price: Legacy.Tr.phrase("199.000đ")}]
            Button {
                objectName: modelData.lifetime ? "plusPlanLifetime" : "plusPlanYearly"
                width: (grid.width - (grid.columns - 1) * grid.spacing) / grid.columns
                height: labels.implicitHeight + 28
                label: ""
                selected: root.lifetime === modelData.lifetime
                clickable: !paymentBridge.busy
                Accessible.name: "Nostalgia+, " + modelData.duration + ", " + modelData.price
                onClicked: paymentBridge.selectPlan(modelData.lifetime)
                Column {
                    id: labels
                    x: 14; y: 14; width: parent.width - 28; spacing: 5
                    PaymentText { width: parent.width; text: modelData.duration; color: root.lifetime === modelData.lifetime ? GlassTheme.accent : GlassTheme.muted; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: modelData.price; font.pixelSize: GlassTheme.fontTitle; font.weight: Font.DemiBold }
                }
            }
        }
    }
    Glass {
        objectName: "plusComparison"
        width: parent.width
        padding: 14
        implicitHeight: table.implicitHeight + 28
        height: implicitHeight
        Column {
            id: table
            width: parent.width; spacing: 8
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mọi thứ chạy trên máy bạn đều miễn phí."); font.weight: Font.DemiBold }
            Grid {
                id: rows
                width: parent.width
                columns: 3
                columnSpacing: 12; rowSpacing: 6
                readonly property real side: Math.max(90 * GlassTheme.scale, width * 0.2)
                Repeater {
                    model: ["", Legacy.Tr.phrase("Miễn phí"), "Nostalgia+",
                            Legacy.Tr.phrase("Chơi, cài mod và modpack, quản lý bản chơi"), "✓", "✓",
                            Legacy.Tr.phrase("Chơi chung, mở server trên máy bạn"), "✓", "✓",
                            Legacy.Tr.phrase("Bộ cosmetic hồ sơ cao cấp và màu hồ sơ"), "—", "✓",
                            Legacy.Tr.phrase("Huy hiệu Nostalgia+ trên hồ sơ"), "—", "✓",
                            Legacy.Tr.phrase("Dùng thử bản launcher mới sớm"), "—", "✓"]
                    PaymentText {
                        readonly property int column: index % 3
                        width: column === 0 ? rows.width - 2 * (rows.side + rows.columnSpacing) : rows.side
                        text: modelData
                        horizontalAlignment: column === 0 ? Text.AlignLeft : Text.AlignHCenter
                        color: column === 2 ? GlassTheme.accent : column === 1 ? GlassTheme.muted : GlassTheme.text
                        font.pixelSize: GlassTheme.fontLabel
                    }
                }
            }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Quyền lợi gắn tài khoản Google · Không tự động gia hạn."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        }
    }
}
