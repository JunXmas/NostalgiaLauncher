import QtQuick

Column {
    width: parent.width
    spacing: 12
    visible: typeof serviceConfiguration !== "undefined"
    PaymentText { width: parent.width; font.weight: Font.DemiBold; text: "Tài khoản Nostalgia" }
    PaymentText { objectName: "serviceStatus"; width: parent.width; text: typeof socialBridge !== "undefined" && socialBridge.configured ? "Google đã được tích hợp. Đăng nhập trong mục Bạn bè hoặc màn hình chào." : "Đăng nhập Google chưa khả dụng trong bản thử này. Chờ bản cập nhật từ Nostalgia."; color: GlassTheme.muted }
    PaymentText { width: parent.width; visible: typeof plusFeaturesEnabled !== "undefined" && !plusFeaturesEnabled; text: "Plus tạm thời vô hiệu hóa. Bản thử này không nhận thanh toán Plus."; color: GlassTheme.muted }
}
