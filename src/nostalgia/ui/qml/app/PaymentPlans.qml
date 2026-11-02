import QtQuick
import "../" as Legacy

Column {
    id: root
    spacing: 10
    property var details: paymentBridge.details
    readonly property bool lifetime: details.lifetime === true
    function money(amount) { return Number(amount).toLocaleString(Qt.locale(Legacy.Tr.localeName), "f", 0) + Legacy.Tr.phrase("đ"); }
    Grid {
        id: grid
        width: parent.width
        columns: width > 420 * GlassTheme.scale ? 2 : 1
        spacing: 10
        Repeater {
            // Giá in sẵn chỉ để hiện trước khi máy chủ trả lời; ô đang chọn luôn hiện giá máy chủ báo.
            model: [{lifetime: false, duration: Legacy.Tr.phrase("1 năm"), amount: 79000},
                    {lifetime: true, duration: Legacy.Tr.phrase("Mua đứt"), amount: 199000}]
            Button {
                id: plan
                readonly property bool chosen: root.lifetime === modelData.lifetime
                objectName: modelData.lifetime ? "plusPlanLifetime" : "plusPlanYearly"
                width: (grid.width - (grid.columns - 1) * grid.spacing) / grid.columns
                height: labels.implicitHeight + 28
                label: ""
                selected: chosen
                clickable: !paymentBridge.busy
                Accessible.name: "Nostalgia+, " + modelData.duration + ", " + root.money(chosen ? root.details.amount : modelData.amount)
                onClicked: paymentBridge.selectPlan(modelData.lifetime)
                Column {
                    id: labels
                    x: 14; y: 14; width: parent.width - 28; spacing: 5
                    PaymentText { width: parent.width; text: modelData.duration; color: plan.chosen ? GlassTheme.accent : GlassTheme.muted; font.weight: Font.DemiBold }
                    PaymentText { objectName: plan.chosen ? "paymentPrice" : ""; width: parent.width; text: root.money(plan.chosen ? root.details.amount : modelData.amount); font.pixelSize: GlassTheme.fontTitle; font.weight: Font.DemiBold }
                }
            }
        }
    }
    PaymentText {
        objectName: "plusTerms"
        width: parent.width
        text: [root.details.upgradeCredit > 0 ? Legacy.Tr.format("Đã khấu trừ %1đ từ gói đã mua còn hiệu lực. Thời hạn gói mới bắt đầu khi được kích hoạt.", [Number(root.details.upgradeCredit).toLocaleString(Qt.locale(Legacy.Tr.localeName), "f", 0)]) : "",
               root.details.eligible === false ? Legacy.Tr.phrase("Tài khoản của bạn đã có Nostalgia+ dài hơn gói này.") : "",
               root.lifetime ? Legacy.Tr.phrase("Gắn với tài khoản Google, dùng trong suốt thời gian dịch vụ hoạt động.") : Legacy.Tr.phrase("Quyền lợi gắn tài khoản Google · Không tự động gia hạn."),
               root.details.amount === 0 && root.details.isUpgrade ? Legacy.Tr.phrase("Khoản khấu trừ đủ cho gói mới. Xác nhận để nâng cấp, không cần chuyển khoản thêm.") : root.details.available ? Legacy.Tr.phrase("Nostalgia+ được kích hoạt sau khi người quản trị đối chiếu tiền vào Vietcombank và duyệt đơn.") : Legacy.Tr.phrase("Đăng nhập Google để tạo đơn và nhận Nostalgia+ trên tài khoản của bạn.")]
              .filter(function (line) { return line.length > 0; }).join("\n")
        color: GlassTheme.muted
        font.pixelSize: GlassTheme.fontNote
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
                            Legacy.Tr.phrase("Huy hiệu Nostalgia+ trên hồ sơ"), "—", "✓"]
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
        }
    }
}
