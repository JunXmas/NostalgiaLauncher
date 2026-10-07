import QtQuick

Column {
    id: root
    spacing: 10
    readonly property int selected: paymentBridge.details.months
    readonly property var extra: ["Chọn 1 trong 3 bộ cosmetic hồ sơ"].concat(selected === 0 ? ["Host server · Plugin & mod", "Huy hiệu Sáng lập & màu hồ sơ", "Tham gia preview sớm", "Các cập nhật Plus về sau"]
        : selected === 12 ? ["Host server · Plugin & mod", "Huy hiệu Tiên phong & màu hồ sơ", "Tham gia preview sớm"]
        : selected === 6 ? ["Host server · Plugin & mod", "Huy hiệu Đồng hành & màu hồ sơ"] : ["Toàn bộ tính năng Plus cốt lõi"])
    Grid {
        id: grid
        width: parent.width
        columns: width > 720 * GlassTheme.scale ? 4 : width > 420 * GlassTheme.scale ? 2 : 1
        spacing: 10
        Repeater {
            model: [{months: 1, title: "Plus", duration: "1 tháng", price: "29.000đ"},
                    {months: 6, title: "Pro", duration: "6 tháng", price: "69.000đ"},
                    {months: 12, title: "Max", duration: "1 năm", price: "109.000đ"},
                    {months: 0, title: "Ultimate", duration: "Mua đứt", price: "209.000đ"}]
            Button {
                objectName: "plusPlan-" + modelData.months
                width: (grid.width - (grid.columns - 1) * grid.spacing) / grid.columns
                height: labels.implicitHeight + 28
                label: ""
                selected: root.selected === modelData.months
                clickable: !paymentBridge.busy
                Accessible.name: modelData.title + ", " + modelData.duration + ", " + modelData.price
                onClicked: paymentBridge.selectPlan(modelData.months)
                Column {
                    id: labels
                    x: 14; y: 14; width: parent.width - 28; spacing: 5
                    PaymentText { width: parent.width; text: modelData.title; color: root.selected === modelData.months ? GlassTheme.accent : GlassTheme.muted; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: modelData.price; font.pixelSize: GlassTheme.fontTitle; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: modelData.duration; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontNote }
                }
            }
        }
    }
    Glass {
        width: parent.width
        padding: 14
        implicitHeight: perks.implicitHeight + 28
        height: implicitHeight
        Column {
            id: perks
            width: parent.width; spacing: 7
            PaymentText { width: parent.width; text: "QUYỀN LỢI RIÊNG · " + paymentBridge.details.planName.toUpperCase(); color: GlassTheme.accent; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
            Flow {
                width: parent.width; spacing: 12
                Repeater { model: root.extra; PaymentText { text: "✓ " + modelData; font.pixelSize: GlassTheme.fontLabel } }
            }
            PaymentText { width: parent.width; text: "Quyền lợi gắn tài khoản Google · Không tự động gia hạn. Server chạy trên máy bạn; không kèm VPS."; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        }
    }
}
