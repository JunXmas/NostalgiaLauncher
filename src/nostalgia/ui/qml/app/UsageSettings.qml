import QtQuick
import "../" as Legacy

Glass {
    width: parent.width
    height: body.implicitHeight + 40
    padding: 20
    frosted: false
    Column {
        id: body
        width: parent.width
        spacing: 12
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Giúp cải thiện Nostalgia"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
        Row {
            spacing: 12
            Legacy.Toggle {
                objectName: "usageStatisticsToggle"
                accessibleLabel: Legacy.Tr.phrase("Chia sẻ thống kê sử dụng tùy chọn")
                checked: usageBridge.choice === "accepted"
                enabled: usageBridge.available || checked
                onToggled: function(checked) { usageBridge.choose(checked); }
            }
            PaymentText { text: usageBridge.choice === "accepted" ? Legacy.Tr.phrase("Đã đồng ý") : usageBridge.choice === "declined" ? Legacy.Tr.phrase("Đã từ chối") : Legacy.Tr.phrase("Chưa lựa chọn"); color: GlassTheme.muted }
        }
        PaymentText {
            width: parent.width
            text: Legacy.Tr.phrase("Chỉ đếm bản cài tự nguyện tham gia hoạt động/ngày: ngày UTC, phiên bản launcher, nhóm hệ điều hành và mã ngẫu nhiên trong ngày. Bạn có thể tắt bất kỳ lúc nào.")
            color: GlassTheme.muted
        }
        PaymentText {
            width: parent.width
            text: usageBridge.available ? Legacy.Tr.phrase("Nơi nhận: ") + usageBridge.endpoint : Legacy.Tr.phrase("Luồng thống kê tùy chọn chưa được kích hoạt. Launcher không gửi sự kiện tới endpoint thống kê mới.")
            color: GlassTheme.muted
        }
        PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mã chống đếm lặp có hạn 24 giờ, dọn hằng giờ. Số liệu tổng hợp giữ 90 ngày. Đăng nhập, cập nhật, tải nội dung và phòng chơi hoạt động độc lập với lựa chọn này."); color: GlassTheme.muted }
        Button { objectName: "viewUsagePayload"; label: Legacy.Tr.phrase("Xem dữ liệu được gửi"); quiet: true; onClicked: usageBridge.showPayload() }
        Button { objectName: "usageSettingsDecline"; visible: usageBridge.choice === "unselected"; label: Legacy.Tr.phrase("Không gửi"); onClicked: usageBridge.choose(false) }
    }
}
