import QtQuick
import "../" as Legacy

Column {
    id: root
    spacing: 10
    readonly property int selected: paymentBridge.details.months
    readonly property var extra: [Legacy.Tr.phrase("Chọn 1 trong 3 bộ cosmetic hồ sơ")].concat(selected === 0 ? [Legacy.Tr.phrase("Host server · Plugin & mod"), Legacy.Tr.phrase("Huy hiệu Sáng lập & màu hồ sơ"), Legacy.Tr.phrase("Tham gia preview sớm"), Legacy.Tr.phrase("Các cập nhật Plus về sau")]
        : selected === 12 ? [Legacy.Tr.phrase("Host server · Plugin & mod"), Legacy.Tr.phrase("Huy hiệu Tiên phong & màu hồ sơ"), Legacy.Tr.phrase("Tham gia preview sớm")]
        : selected === 6 ? [Legacy.Tr.phrase("Host server · Plugin & mod"), Legacy.Tr.phrase("Huy hiệu Đồng hành & màu hồ sơ")] : [Legacy.Tr.phrase("Toàn bộ tính năng Plus cốt lõi")])
    Grid {
        id: grid
        width: parent.width
        columns: width > 720 * GlassTheme.scale ? 4 : width > 420 * GlassTheme.scale ? 2 : 1
        spacing: 10
        Repeater {
            model: [{months: 1, title: "Plus", duration: Legacy.Tr.phrase("1 tháng"), price: Legacy.Tr.phrase("29.000đ")},
                    {months: 6, title: "Pro", duration: Legacy.Tr.phrase("6 tháng"), price: Legacy.Tr.phrase("69.000đ")},
                    {months: 12, title: "Max", duration: Legacy.Tr.phrase("1 năm"), price: Legacy.Tr.phrase("109.000đ")},
                    {months: 0, title: "Ultimate", duration: Legacy.Tr.phrase("Mua đứt"), price: Legacy.Tr.phrase("209.000đ")}]
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
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("QUYỀN LỢI RIÊNG · ") + paymentBridge.details.planName.toUpperCase(); color: GlassTheme.accent; font.pixelSize: GlassTheme.fontCaption; font.letterSpacing: 1 }
            Flow {
                width: parent.width; spacing: 12
                Repeater { model: root.extra; PaymentText { text: "✓ " + modelData; font.pixelSize: GlassTheme.fontLabel } }
            }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Quyền lợi gắn tài khoản Google · Không tự động gia hạn. Server chạy trên máy bạn; không kèm VPS."); color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
        }
    }
}
