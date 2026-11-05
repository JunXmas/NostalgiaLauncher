import QtQuick
import "../" as Legacy

Glass {
    id: card
    objectName: "usageSettingsCard"
    readonly property string choiceLabel: usageBridge.choice === "accepted" ? Legacy.Tr.phrase("Đã đồng ý") : usageBridge.choice === "declined" ? Legacy.Tr.phrase("Đã từ chối") : Legacy.Tr.phrase("Chưa lựa chọn")
    width: parent.width
    height: body.implicitHeight + 40
    padding: 20
    frosted: false
    Column {
        id: body
        width: parent.width
        spacing: 12
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Giúp cải thiện Nostalgia"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
        UsagePurpose {}
        PaymentText {
            objectName: "usageUnavailableStatus"
            visible: !usageBridge.available
            width: parent.width
            text: Legacy.Tr.phrase("Chưa khả dụng")
            font.weight: Font.DemiBold
        }
        Row {
            visible: usageBridge.available
            spacing: 12
            Legacy.Toggle {
                objectName: "usageStatisticsToggle"
                accessibleLabel: Legacy.Tr.phrase("Chia sẻ thống kê sử dụng tùy chọn")
                checked: usageBridge.choice === "accepted"
                onToggled: function(checked) { usageBridge.choose(checked); }
            }
            PaymentText { text: card.choiceLabel; color: GlassTheme.muted }
        }
        PaymentText { width: parent.width; visible: !usageBridge.available && usageBridge.choice !== "unselected"; text: Legacy.Tr.phrase("Lựa chọn đã lưu: ") + card.choiceLabel; color: GlassTheme.muted }
        PaymentText {
            width: parent.width
            text: Legacy.Tr.phrase("Khi bạn đồng ý chia sẻ, dữ liệu chỉ gồm ngày UTC, phiên bản launcher, nhóm hệ điều hành và mã ngẫu nhiên theo ngày.")
            color: GlassTheme.muted
        }
        PaymentText {
            width: parent.width
            text: usageBridge.available ? Legacy.Tr.phrase("Nơi nhận: ") + usageBridge.endpoint : Legacy.Tr.phrase("Dịch vụ thống kê chưa được triển khai nên hiện chưa thể bật. Launcher không gửi sự kiện tới endpoint thống kê mới. Lựa chọn đã lưu của bạn được giữ nguyên.")
            color: GlassTheme.muted
        }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mã chống đếm lặp có hạn 24 giờ, dọn hằng giờ. Số liệu tổng hợp giữ 90 ngày. Đăng nhập, cập nhật, tải nội dung và phòng chơi hoạt động độc lập với lựa chọn này."); color: GlassTheme.muted }
        Button { objectName: "viewUsagePayload"; label: Legacy.Tr.phrase("Xem dữ liệu được gửi"); quiet: true; onClicked: usageBridge.showPayload() }
        Button { objectName: "usageSettingsDecline"; visible: usageBridge.choice === "unselected" || (!usageBridge.available && usageBridge.choice === "accepted"); label: Legacy.Tr.phrase("Không gửi"); onClicked: usageBridge.choose(false) }
    }
}
